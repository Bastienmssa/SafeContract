"""
Point d'entree unique du module GNN pour integration dans un projet existant.

Usage depuis un backend Python (FastAPI, Flask...) :
    from gnn_service import analyser_contrat
    resultat = analyser_contrat("/chemin/vers/Contrat.sol", "/chemin/vers/rapport_outils.json")

Usage en ligne de commande (appelable depuis Node.js via subprocess) :
    python gnn_service.py /chemin/Contrat.sol [/chemin/rapport_outils.json]

Le JSON retourne :
{
  "success": true,
  "contrat": "Contrat.sol",
  "findings": [
    {
      "niveau":   "CONFIRMED" | "POTENTIAL" | "FILTERED",
      "lignes":   [9],
      "type_noeud": "NodeType.EXPRESSION",
      "code":     "msg.sender.call{value: bal}()",
      "prob_gnn": 0.931,          // null si finding outil seul
      "outils":   ["mythril", "slither"],
      "details":  [
        {"outil": "mythril", "swc": "SWC-107", "severite": "medium", "titre": "..."},
        {"outil": "slither", "swc": "SWC-107", "severite": "high",   "titre": "..."}
      ]
    }
  ],
  "resume": {
    "confirmed":  1,
    "potential":  0,
    "filtered":   0
  },
  "erreur": null
}
"""

import sys
import os
import json
import shutil
import tempfile
import torch

# Permettre l'import depuis n'importe quel repertoire
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.live_extractor import extraire_contrat_local
from src.live_vectorizer import vectoriser_graphes
from src.predict import (
    parser_rapport_outils,
    _construire_predecesseurs,
    _construire_successeurs,
    _est_operation_dangereuse,
    _est_protege,
    _est_protege_swc,
    _SEUIL_POTENTIEL,
)
from src.models.gnn_model import SmartContractGNN
from src.config import DIM_TOTALE, SEUIL_DEFAUT

CHEMIN_MODELE = os.path.join(os.path.dirname(__file__), "models", "gnn_smart_contracts_v6_retrain.pth")
_TYPES_EXCLUS = {"nodetype.entrypoint", "nodetype.startloop", "nodetype.endloop"}


def analyser_contrat(chemin_sol: str, chemin_rapport: str = None) -> dict:
    """
    Analyse un contrat Solidity et retourne les failles detectees en JSON.

    Parametres
    ----------
    chemin_sol     : chemin absolu ou relatif vers le fichier .sol
    chemin_rapport : (optionnel) chemin vers le JSON du rapport outils
                     (format unifie backend OU JSON Mythril brut)

    Retourne
    --------
    dict avec les champs "success", "findings", "resume", "erreur"
    """
    nom = os.path.basename(chemin_sol)

    # Dossier temporaire isole pour ce contrat
    with tempfile.TemporaryDirectory() as tmpdir:
        chemin_json = os.path.join(tmpdir, "graphe.json")
        chemin_pt   = os.path.join(tmpdir, "graphe.pt")
        # Copie dans un sous-dossier dédié : imports relatifs (./X.sol) résolus au même endroit
        work = os.path.join(tmpdir, "workspace")
        os.makedirs(work, exist_ok=True)
        chemin_local = os.path.join(work, nom)
        try:
            shutil.copy2(chemin_sol, chemin_local)
        except OSError as e:
            return {"success": False, "contrat": nom, "findings": [], "resume": {}, "erreur": f"Copie contrat : {e}"}

        # Phase 1 : extraction Slither (+ fallback graphe source si échec)
        try:
            succes = extraire_contrat_local(chemin_local, chemin_json)
            if not succes:
                return {"success": False, "contrat": nom, "findings": [], "resume": {}, "erreur": "Echec extraction Slither"}
        except Exception as e:
            return {"success": False, "contrat": nom, "findings": [], "resume": {}, "erreur": f"Slither : {e}"}

        # Phase 2 : vectorisation CodeBERT
        try:
            vectoriser_graphes(chemin_json, chemin_pt)
        except Exception as e:
            return {"success": False, "contrat": nom, "findings": [], "resume": {}, "erreur": f"Vectorisation : {e}"}

        # Phase 3 : prediction GNN + fusion outils
        try:
            findings, resume = _predire(chemin_pt, chemin_json, chemin_rapport)
        except Exception as e:
            return {"success": False, "contrat": nom, "findings": [], "resume": {}, "erreur": f"Prediction : {e}"}

    return {
        "success":  True,
        "contrat":  nom,
        "findings": findings,
        "resume":   resume,
        "erreur":   None,
    }


def _predire(chemin_pt, chemin_json, chemin_rapport):
    """Prediction interne — retourne (findings, resume)."""
    appareil = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    donnees = torch.load(chemin_pt, map_location=appareil, weights_only=False)
    x, edge_index = donnees['x'].to(appareil), donnees['edge_index'].to(appareil)

    modele = SmartContractGNN(in_channels=DIM_TOTALE, hidden_channels=128, out_channels=2).to(appareil)
    modele.load_state_dict(torch.load(CHEMIN_MODELE, map_location=appareil, weights_only=True))
    modele.eval()

    with torch.no_grad():
        probs = torch.softmax(modele(x, edge_index), dim=1)[:, 1]

    with open(chemin_json, 'r', encoding='utf-8') as f:
        data_json = json.load(f)

    noeuds        = data_json[list(data_json.keys())[0]].get("graphe_noeuds", [])
    predecesseurs = _construire_predecesseurs(edge_index)
    successeurs   = _construire_successeurs(edge_index)
    rapport_outils = parser_rapport_outils(chemin_rapport) if chemin_rapport else {}

    # Mapper chaque ligne outil -> noeud le plus specifique
    ligne_vers_noeud = {}
    for i, noeud in enumerate(noeuds):
        if noeud.get("type", "").lower() in _TYPES_EXCLUS:
            continue
        for ligne in noeud.get("lignes", []):
            if ligne not in rapport_outils:
                continue
            a_op = _est_operation_dangereuse(noeud)
            actuel = ligne_vers_noeud.get(ligne)
            if actuel is None or (a_op and not actuel[1]):
                ligne_vers_noeud[ligne] = (i, a_op)

    outils_par_noeud = {}
    for ligne, (idx, _) in ligne_vers_noeud.items():
        vus = {(iss["title"].lower()[:60], iss["swc_id"]) for iss in outils_par_noeud.get(idx, [])}
        for issue in rapport_outils[ligne]:
            cle = (issue["title"].lower()[:60], issue["swc_id"])
            if cle not in vus:
                vus.add(cle)
                outils_par_noeud.setdefault(idx, []).append(issue)

    lignes_couvertes = set(rapport_outils.keys())
    resultats = {}

    for i, prob in enumerate(probs):
        noeud = noeuds[i]
        texte = (noeud.get("contenu", "") + " " + noeud.get("type", "")).lower()
        lignes_noeud = set(noeud.get("lignes", []))

        est_override = any(p in texte for p in [
            "tx.origin", "blockhash", "block.difficulty", "block.prevrandao", "selfdestruct", "unchecked"
        ])
        score_ok = prob.item() >= SEUIL_DEFAUT or est_override

        if score_ok and _est_operation_dangereuse(noeud) and not _est_protege(i, noeuds, predecesseurs, successeurs):
            resultats.setdefault(i, {"prob": prob.item(), "gnn": False, "outils": [], "filtrees": []})
            resultats[i]["gnn"] = True

        if i in outils_par_noeud:
            for swc_id in {iss["swc_id"] for iss in outils_par_noeud[i]}:
                a_op = _est_operation_dangereuse(noeud)
                protege = _est_protege(i, noeuds, predecesseurs, successeurs) if a_op else \
                          _est_protege_swc(i, noeuds, predecesseurs, successeurs, swc_id)
                entree = resultats.setdefault(i, {"prob": prob.item(), "gnn": False, "outils": [], "filtrees": []})
                issues_swc = [iss for iss in outils_par_noeud[i] if iss["swc_id"] == swc_id]
                cible = entree["filtrees"] if protege else entree["outils"]
                for iss in issues_swc:
                    if iss not in cible:
                        cible.append(iss)

    # Construire la liste de findings
    findings  = []
    compteurs = {"confirmed": 0, "potential": 0, "filtered": 0}

    def _premiere_ligne(idx):
        l = noeuds[idx].get("lignes", [])
        return l[0] if l else 0

    for i in sorted(resultats, key=_premiere_ligne):
        info  = resultats[i]
        noeud = noeuds[i]

        a_outil  = bool(info["outils"])
        a_gnn    = info["gnn"]
        a_filtre = bool(info["filtrees"]) and not a_outil

        if a_outil:
            niveau = "CONFIRMED"
        elif a_gnn and info["prob"] >= _SEUIL_POTENTIEL:
            niveau = "POTENTIAL"
        elif a_filtre:
            niveau = "FILTERED"
        else:
            continue

        compteurs[niveau.lower()] += 1

        findings.append({
            "niveau":     niveau,
            "lignes":     noeud.get("lignes", []),
            "type_noeud": noeud.get("type", ""),
            "code":       noeud.get("contenu", "").strip()[:80],
            "prob_gnn":   round(info["prob"], 4) if a_gnn else None,
            "outils":     sorted({iss["tool"] for iss in info["outils"]}) if a_outil else [],
            "details":    [
                {
                    "outil":    iss["tool"],
                    "swc":      f"SWC-{iss['swc_id']}" if iss["swc_id"] else "",
                    "severite": iss["severity"],
                    "titre":    iss["title"],
                }
                for iss in (info["outils"] if a_outil else info["filtrees"])
            ],
        })

    return findings, compteurs


# ---------------------------------------------------------------------------
# Mode ligne de commande (appelable depuis Node.js via child_process)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "erreur": "Usage : python gnn_service.py <contrat.sol> [rapport.json]"}))
        sys.exit(1)

    chemin_sol     = sys.argv[1]
    chemin_rapport = sys.argv[2] if len(sys.argv) >= 3 else None

    resultat = analyser_contrat(chemin_sol, chemin_rapport)
    print(json.dumps(resultat, ensure_ascii=False, indent=2))
