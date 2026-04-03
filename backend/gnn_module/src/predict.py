import torch
import json
import os
from src.models.gnn_model import SmartContractGNN
from src.config import DIM_TOTALE

# ---------------------------------------------------------------------------
# Filtre Topologique (deux couches)
#
# Couche 1 : ne conserver que les noeuds contenant une operation dangereuse.
#
# Couche 2 : BFS arriere/avant sur le CFG.
#   - Si un predecesseur contient une protection connue  -> alerte supprimee.
#   - Pour ecrecover : BFS avant pour verifier address(0).
#
# Integration outils (Mythril / Slither / Foundry / Echidna / Solhint) :
#   Les findings du JSON unifie bypassent le seuil de confiance du GNN mais
#   passent toujours par la Couche 2 pour eliminer les faux positifs outillages.
#
# Niveaux de confiance du rapport final :
#   CONFIRMED  : au moins un outil ET la topologie CFG s'accordent.
#   POTENTIAL  : GNN seul (>= 80 %), aucun outil ne couvre cette ligne.
#   FILTERED   : outil a signale la ligne MAIS la topologie indique une
#                protection -> faux positif probable, note uniquement.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 1. Constantes des filtres topologiques
# ---------------------------------------------------------------------------

_OPS_DANGEREUSES = [
    ".call{", "msg.sender.call", ".call(",
    ".send(",
    ".transfer(",
    "ecrecover",
    "selfdestruct",
    "delegatecall",
    "tx.origin",
    "block.timestamp",
    "blockhash",
    "block.difficulty",
    "block.prevrandao",
    "unchecked",
    "swapexacttokens", "swaptokens",
    "latestrounddata",
]

_PROTECTIONS_REENTRANCY = [
    "nonreentrant",
    "_status != 2",
    "reentrancyguard",
    "] = 0",
]

_PROTECTIONS_REPLAY = [
    "nonce",
    "usednonces",
    "usedsignatures",
    "executed[",
]

_PROTECTIONS_ACCESS = [
    "msg.sender == owner",
    "require(msg.sender ==",
    "onlyowner",
    "require(owner",
    "require(owner ==",
    "onlyadmin",
    "_checkowner",
]

# Mapping nom de detecteur Slither -> SWC numerique (sans "SWC-")
# Utilise pour router vers la bonne protection Layer 2
_SLITHER_VERS_SWC = {
    "reentrancy-eth":           "107",
    "reentrancy-no-eth":        "107",
    "reentrancy-benign":        "107",
    "reentrancy-events":        "107",
    "reentrancy-unlimited-gas": "107",
    "arbitrary-send-eth":       "105",
    "arbitrary-send-erc20":     "105",
    "suicidal":                 "106",
    "controlled-delegatecall":  "112",
    "delegatecall-loop":        "107",
    "timestamp":                "116",
    "tx-origin":                "115",
    "weak-prng":                "120",
    "unchecked-send":           "104",
    "unchecked-lowlevel":       "104",
    "integer-overflow":         "101",
    "tautology":                "127",
    "incorrect-equality":       "132",
    "abiencoderv2-array":       "133",
    "msg-value-loop":           "113",
}

# Hint SWC -> operations attendues (pour Layer 2 sur noeuds sans op reconnue)
_SWC_OPS_HINT = {
    "104": [".call{", ".call(", ".send("],
    "107": [".call{", "msg.sender.call", ".call(", ".send("],
    "105": [".transfer("],
    "106": ["selfdestruct"],
    "112": ["delegatecall"],
    "115": ["tx.origin"],
    "116": ["block.timestamp"],
    "117": ["ecrecover"],
    "120": ["blockhash", "block.difficulty"],
    "122": ["ecrecover"],
}

# Seuil de confiance minimal pour un finding GNN-seul (sans outil)
_SEUIL_POTENTIEL = 0.80


# ---------------------------------------------------------------------------
# 2. Parseur du rapport JSON unifie (auto-detection du format)
# ---------------------------------------------------------------------------

def _normaliser_severity(brute: str) -> str:
    """Ramene toutes les variantes de severite a critical/high/medium/low."""
    s = brute.lower().strip()
    if s in ("critical", "high"):
        return s
    if s in ("medium", "moderate"):
        return "medium"
    return "low"


def _extraire_swc_depuis_titre_slither(titre: str) -> str:
    """Retourne le SWC numerique correspondant a un detecteur Slither, ou ''."""
    return _SLITHER_VERS_SWC.get(titre.lower().strip(), "")


def parser_rapport_outils(chemin_json: str) -> dict:
    """
    Parse le JSON produit par le backend (format unifie) OU le JSON brut Mythril.
    Retourne { lineno (int) : [ {swc_id, title, severity, tool, confidence}, ... ] }

    Formats geres :
      - Format unifie  : {"report": {"issues": [{"line": ..., "swcId": ..., ...}]}}
      - Format Mythril : {"report": {"issues": [{"lineno": ..., "swc-id": ..., ...}]}}
      - Format liste   : [{"lineno": ..., "swc-id": ...}, ...]
    """
    if not chemin_json or not os.path.isfile(chemin_json):
        return {}

    try:
        with open(chemin_json, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}

    # --- Detecter et extraire la liste brute d'issues ---
    issues_brutes = []
    if isinstance(data, list):
        issues_brutes = data
    elif isinstance(data, dict):
        if "report" in data and isinstance(data["report"], dict):
            issues_brutes = data["report"].get("issues", [])
        elif "issues" in data:
            issues_brutes = data["issues"]

    # --- Normaliser chaque issue ---
    par_ligne = {}
    for issue in issues_brutes:
        # Champ ligne : "line" (unifie) ou "lineno" (Mythril brut)
        ligne = issue.get("line") or issue.get("lineno")
        if not ligne:
            continue
        try:
            ligne = int(ligne)
        except (ValueError, TypeError):
            continue

        # SWC : "swcId" (unifie, ex: "SWC-107") ou "swc-id" (Mythril brut, ex: "107")
        swc_brut = str(issue.get("swcId") or issue.get("swc-id") or "")
        swc_id = swc_brut.replace("SWC-", "").strip()

        # Si Slither (swcId vide), tenter le mapping par titre detecteur
        titre = issue.get("title", "")
        if not swc_id:
            swc_id = _extraire_swc_depuis_titre_slither(titre)

        outil = str(issue.get("tool", "unknown")).lower()
        severity = _normaliser_severity(str(issue.get("severity", "low")))
        confidence = str(issue.get("confidence", "")).lower()

        normalise = {
            "swc_id":     swc_id,
            "title":      titre,
            "severity":   severity,
            "tool":       outil,
            "confidence": confidence,
            "description": issue.get("description", ""),
        }

        # Deduplication par (titre[:60], swc_id) sur la meme ligne
        existants = par_ligne.setdefault(ligne, [])
        cle = (titre.lower()[:60], swc_id)
        if not any((e["title"].lower()[:60], e["swc_id"]) == cle for e in existants):
            existants.append(normalise)

    return par_ligne


# ---------------------------------------------------------------------------
# 3. Constructeurs de maps CFG
# ---------------------------------------------------------------------------

def _construire_predecesseurs(edge_index: torch.Tensor) -> dict:
    preds = {}
    if edge_index.shape[1] == 0:
        return preds
    for src, dst in zip(*edge_index.cpu().tolist()):
        preds.setdefault(dst, []).append(src)
    return preds


def _construire_successeurs(edge_index: torch.Tensor) -> dict:
    succs = {}
    if edge_index.shape[1] == 0:
        return succs
    for src, dst in zip(*edge_index.cpu().tolist()):
        succs.setdefault(src, []).append(dst)
    return succs


# ---------------------------------------------------------------------------
# 4. Filtre Couche 1
# ---------------------------------------------------------------------------

def _est_operation_dangereuse(noeud: dict) -> bool:
    texte = (noeud.get("contenu", "") + " " + noeud.get("type", "")).lower()
    if not any(op in texte for op in _OPS_DANGEREUSES):
        return False
    # Raffinement SWC-116 : block.timestamp >= est un delai acceptable
    autres = [op for op in _OPS_DANGEREUSES if op != "block.timestamp"]
    if "block.timestamp" in texte and not any(op in texte for op in autres):
        if ">=" in texte and "==" not in texte:
            return False
    return True


# ---------------------------------------------------------------------------
# 5. Filtre Couche 2 : BFS arriere et avant
# ---------------------------------------------------------------------------

def _bfs(idx, noeuds, voisins_map, mots_cles, profondeur):
    visites, file = set(), [idx]
    for _ in range(profondeur):
        prochains = []
        for n in file:
            if n in visites:
                continue
            visites.add(n)
            for v in voisins_map.get(n, []):
                if v in visites:
                    continue
                texte = (noeuds[v].get("contenu", "") + " " + noeuds[v].get("type", "")).lower()
                if any(m in texte for m in mots_cles):
                    return True
                prochains.append(v)
        file = prochains
        if not file:
            break
    return False


def _est_protege(idx, noeuds, predecesseurs, successeurs):
    texte = (noeuds[idx].get("contenu", "") + " " + noeuds[idx].get("type", "")).lower()

    if "ecrecover" in texte:
        if any(m in texte for m in _PROTECTIONS_REPLAY):
            return True
        if _bfs(idx, noeuds, predecesseurs, _PROTECTIONS_REPLAY, 5):
            return True
        if _bfs(idx, noeuds, successeurs, ["address(0)", "address(0x0)", "!= address"], 3):
            return True
        return False
    elif any(op in texte for op in [".call{", "msg.sender.call", ".call(", ".send("]):
        return _bfs(idx, noeuds, predecesseurs, _PROTECTIONS_REENTRANCY, 5)
    elif any(op in texte for op in [".transfer(", "selfdestruct", "delegatecall"]):
        return _bfs(idx, noeuds, predecesseurs, _PROTECTIONS_ACCESS, 5)
    return False


def _est_protege_swc(idx, noeuds, predecesseurs, successeurs, swc_id):
    """Variante de _est_protege guidee par le SWC-ID (pour les noeuds sans op reconnue)."""
    texte = (noeuds[idx].get("contenu", "") + " " + noeuds[idx].get("type", "")).lower()
    hint = " ".join(_SWC_OPS_HINT.get(swc_id, []))
    augmente = texte + " " + hint

    if "ecrecover" in augmente or swc_id in ("117", "122"):
        if any(m in texte for m in _PROTECTIONS_REPLAY):
            return True
        if _bfs(idx, noeuds, predecesseurs, _PROTECTIONS_REPLAY, 5):
            return True
        if _bfs(idx, noeuds, successeurs, ["address(0)", "!= address"], 3):
            return True
        return False
    elif any(op in augmente for op in [".call{", ".call(", ".send("]) or swc_id in ("107", "104"):
        return _bfs(idx, noeuds, predecesseurs, _PROTECTIONS_REENTRANCY, 5)
    elif any(op in augmente for op in [".transfer(", "selfdestruct", "delegatecall"]) or swc_id in ("105", "106", "112"):
        return _bfs(idx, noeuds, predecesseurs, _PROTECTIONS_ACCESS, 5)
    # SWC-101, SWC-114, SWC-115, SWC-120 etc. : pas de protection topologique connue
    return False


# ---------------------------------------------------------------------------
# 6. Pipeline principal
# ---------------------------------------------------------------------------

def lancer_prediction(
    chemin_pt: str,
    chemin_json: str,
    chemin_modele: str,
    seuil_confiance: float,
    chemin_rapport: str = None,
):
    """
    Prediction GNN + fusion avec le rapport JSON des outils d'analyse.

    Parametres
    ----------
    chemin_pt       : graphe vectorise (.pt)
    chemin_json     : graphe JSON noeuds/aretes (sortie live_extractor)
    chemin_modele   : poids du modele (.pth)
    seuil_confiance : seuil GNN (ex : 0.60)
    chemin_rapport  : (optionnel) JSON unifie du backend ou JSON Mythril brut
    """
    print(f"    [Phase 3] Jugement de l'IA (Seuil : {seuil_confiance*100:.1f}%)")
    if chemin_rapport:
        print(f"    [Outils]  Integration du rapport : {os.path.basename(chemin_rapport)}")

    appareil = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Chargement du graphe et du modele
    donnees = torch.load(chemin_pt, map_location=appareil, weights_only=False)
    x          = donnees['x'].to(appareil)
    edge_index = donnees['edge_index'].to(appareil)

    modele = SmartContractGNN(in_channels=DIM_TOTALE, hidden_channels=128, out_channels=2).to(appareil)
    modele.load_state_dict(torch.load(chemin_modele, map_location=appareil, weights_only=True))
    modele.eval()

    with torch.no_grad():
        probs_vuln = torch.softmax(modele(x, edge_index), dim=1)[:, 1]

    with open(chemin_json, 'r', encoding='utf-8') as f:
        dataset_json = json.load(f)

    nom_contrat = list(dataset_json.keys())[0]
    noeuds      = dataset_json[nom_contrat].get("graphe_noeuds", [])

    predecesseurs = _construire_predecesseurs(edge_index)
    successeurs   = _construire_successeurs(edge_index)

    # --- Parsing du rapport outils ---
    rapport_par_ligne = parser_rapport_outils(chemin_rapport) if chemin_rapport else {}

    # Noeuds structurels exclus du matching outils (couvrent de grandes plages de lignes)
    _TYPES_EXCLUS = {"nodetype.entrypoint", "nodetype.startloop", "nodetype.endloop"}

    # Pour chaque ligne outil, trouver le noeud operationnel le plus specifique
    ligne_vers_noeud = {}
    for i, noeud in enumerate(noeuds):
        if noeud.get("type", "").lower() in _TYPES_EXCLUS:
            continue
        for ligne in noeud.get("lignes", []):
            if ligne not in rapport_par_ligne:
                continue
            a_op = _est_operation_dangereuse(noeud)
            actuel = ligne_vers_noeud.get(ligne)
            if actuel is None or (a_op and not actuel[1]):
                ligne_vers_noeud[ligne] = (i, a_op)

    # Map idx_noeud -> issues outils (dedupliquees)
    outils_par_noeud = {}
    for ligne, (idx, _) in ligne_vers_noeud.items():
        vus = {(iss["title"].lower()[:60], iss["swc_id"]) for iss in outils_par_noeud.get(idx, [])}
        for issue in rapport_par_ligne[ligne]:
            cle = (issue["title"].lower()[:60], issue["swc_id"])
            if cle not in vus:
                vus.add(cle)
                outils_par_noeud.setdefault(idx, []).append(issue)

    # Ensemble des lignes couvertes par au moins un outil (pour logique POTENTIAL)
    lignes_couvertes_outils = set(rapport_par_ligne.keys())

    # -------------------------------------------------------------------
    # Boucle de decision : CONFIRMED / POTENTIAL / FILTERED
    # -------------------------------------------------------------------
    # Structure : { idx -> {"prob": float, "niveau": str, "sources_gnn": bool,
    #                        "issues_outils": list, "filtrees": list} }
    resultats = {}

    for i, prob in enumerate(probs_vuln):
        noeud = noeuds[i]
        texte = (noeud.get("contenu", "") + " " + noeud.get("type", "")).lower()
        lignes_noeud = set(noeud.get("lignes", []))

        # --- Overrides deterministes GNN ---
        est_override = any(p in texte for p in [
            "tx.origin", "blockhash", "block.difficulty", "block.prevrandao",
            "selfdestruct", "unchecked",
        ])
        score_gnn_ok = prob.item() >= seuil_confiance or est_override

        # ========== Chemin GNN ==========
        if score_gnn_ok and _est_operation_dangereuse(noeud):
            protege = _est_protege(i, noeuds, predecesseurs, successeurs)
            if not protege:
                # Lignes de ce noeud deja couvertes par un outil ?
                couverte_par_outil = bool(lignes_noeud & lignes_couvertes_outils)
                resultats.setdefault(i, {
                    "prob": prob.item(), "sources_gnn": False,
                    "issues_outils": [], "filtrees": []
                })
                resultats[i]["sources_gnn"] = True

        # ========== Chemin Outils ==========
        if i in outils_par_noeud:
            issues = outils_par_noeud[i]
            swc_ids = list({iss["swc_id"] for iss in issues})
            for swc_id in swc_ids:
                a_op = _est_operation_dangereuse(noeud)
                if a_op:
                    protege = _est_protege(i, noeuds, predecesseurs, successeurs)
                else:
                    protege = _est_protege_swc(i, noeuds, predecesseurs, successeurs, swc_id)

                issues_swc = [iss for iss in issues if iss["swc_id"] == swc_id]
                entree = resultats.setdefault(i, {
                    "prob": prob.item(), "sources_gnn": False,
                    "issues_outils": [], "filtrees": []
                })
                if protege:
                    # Outil a trouve mais topologie protege : FILTERED
                    for iss in issues_swc:
                        if iss not in entree["filtrees"]:
                            entree["filtrees"].append(iss)
                else:
                    # Confirme par la topologie : ajouter aux issues actives
                    for iss in issues_swc:
                        if iss not in entree["issues_outils"]:
                            entree["issues_outils"].append(iss)

    # -------------------------------------------------------------------
    # Determination du niveau final par noeud
    # -------------------------------------------------------------------
    print("-" * 50)
    alertes_actives = []
    alertes_filtrees = []

    for i, info in resultats.items():
        a_outil  = bool(info["issues_outils"])
        a_gnn    = info["sources_gnn"]
        a_filtre = bool(info["filtrees"])

        if a_outil:
            # Au moins un outil confirme + topologie valide
            if a_gnn:
                niveau = "CONFIRMED"
            else:
                niveau = "CONFIRMED"  # outil seul suffit si topologie OK
            alertes_actives.append((i, niveau, info))
        elif a_gnn:
            # GNN seul — seuil eleve pour eviter les hallucinations
            prob_val = info["prob"]
            lignes_noeud = set(noeuds[i].get("lignes", []))
            non_couverte = not bool(lignes_noeud & lignes_couvertes_outils)
            if prob_val >= _SEUIL_POTENTIEL:
                niveau = "POTENTIAL"
                alertes_actives.append((i, niveau, info))
            # En dessous de 80 % et non confirme par outil -> silencieux

        if a_filtre and not a_outil:
            alertes_filtrees.append((i, info))

    # --- Affichage des alertes actives (triees par ligne) ---
    def _premiere_ligne(idx):
        lignes = noeuds[idx].get("lignes", [])
        return lignes[0] if lignes else 0

    for i, niveau, info in sorted(alertes_actives, key=lambda t: _premiere_ligne(t[0])):
        noeud   = noeuds[i]
        lignes  = noeud.get("lignes", [])
        type_n  = noeud.get("type", "Inconnu")
        contenu = noeud.get("contenu", "").strip()[:60].replace("\n", " ")
        lignes_str = f"Ligne(s) {lignes}" if lignes else "Ligne inconnue"

        if niveau == "CONFIRMED":
            tag = "[!] CONFIRMED"
        else:
            tag = "[?] POTENTIAL"

        prob_str = f" ({info['prob']*100:.1f}%)" if info["sources_gnn"] else ""
        outils_str = ""
        if info["issues_outils"]:
            outils_list = sorted({iss["tool"] for iss in info["issues_outils"]})
            outils_str = " | Outils : " + ", ".join(outils_list)

        print(f"    {tag}{prob_str} | {lignes_str}{outils_str}")
        print(f"        Code : [{type_n}] {contenu}...")

        for iss in info["issues_outils"]:
            swc  = f"SWC-{iss['swc_id']}" if iss["swc_id"] else ""
            sev  = iss["severity"]
            outil = iss["tool"]
            titre = iss["title"]
            swc_str = f" {swc}" if swc else ""
            print(f"        {outil.capitalize()} →{swc_str} ({sev}) : {titre}")

    # --- Affichage des faux positifs filtres (informatif) ---
    if alertes_filtrees:
        print()
        print("    [ Findings outils supprimes par protection topologique ]")
        for i, info in sorted(alertes_filtrees, key=lambda t: _premiere_ligne(t[0])):
            noeud   = noeuds[i]
            lignes  = noeud.get("lignes", [])
            contenu = noeud.get("contenu", "").strip()[:50].replace("\n", " ")
            lignes_str = f"Ligne(s) {lignes}" if lignes else "?"
            for iss in info["filtrees"]:
                swc = f"SWC-{iss['swc_id']}" if iss["swc_id"] else ""
                print(f"    [~] FILTERED | {lignes_str} | {iss['tool']} {swc} ({iss['severity']}) — protection CFG detectee")
                print(f"        Code : {contenu}...")

    if not alertes_actives and not alertes_filtrees:
        print("    [+] Le contrat semble securise (Aucune faille majeure detectee).")

    print("-" * 50)
