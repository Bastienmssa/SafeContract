"""
backend/app/services/ai_service.py

Service IA — integration du modele GNN dans SafeContract.
Appelee depuis scan.py apres l'agregation des outils.

Interface :
    is_available() -> bool
    analyze_contract(contract_path: str, issues: list[dict]) -> dict

Retour :
    {
        "verdict":     "vulnerable" | "safe",
        "score":       int (0-100, score GNN independant du score global),
        "explanation": str,
        "ai_issues":   list[dict]   # meme format que les issues en entree
    }

Configuration :
    Variable d'environnement GNN_MODULE_PATH : chemin absolu vers le dossier
    contenant gnn_service.py et src/. Par defaut : ./gnn_module/
"""

import os
import sys
import json
import tempfile
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Localisation du module GNN
# ---------------------------------------------------------------------------

_GNN_MODULE_PATH = os.environ.get(
    "GNN_MODULE_PATH",
    os.path.dirname(os.path.abspath(__file__)),  # gnn_module/ est le dossier de ce fichier
)
_GNN_MODULE_PATH = os.path.normpath(_GNN_MODULE_PATH)
_CHEMIN_MODELE   = os.path.join(_GNN_MODULE_PATH, "models", "gnn_smart_contracts_v6_retrain.pth")

# Ajout du module GNN au path Python
if _GNN_MODULE_PATH not in sys.path:
    sys.path.insert(0, _GNN_MODULE_PATH)

# Import tardif pour ne pas planter si le module est absent
_gnn_analyser = None

def _charger_module_gnn():
    global _gnn_analyser
    if _gnn_analyser is not None:
        return True
    try:
        from gnn_service import analyser_contrat
        _gnn_analyser = analyser_contrat
        return True
    except Exception as e:
        logger.warning(f"[GNN] Impossible de charger le module : {e}")
        return False


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def get_version() -> str:
    """Retourne la version du modèle GNN chargé."""
    try:
        import torch
        pth = os.path.basename(_CHEMIN_MODELE)
        return f"GNN v6 (torch {torch.__version__})"
    except Exception:
        return "GNN v6"


def is_available() -> bool:
    """
    Retourne True si le modele GNN est charge et pret.
    Passer a True une fois le module GNN installe dans le projet.
    """
    return os.path.isfile(_CHEMIN_MODELE) and _charger_module_gnn()


def analyze_contract(contract_path: str, issues: list[dict]) -> dict:
    """
    Analyse un contrat Solidity avec le modele GNN.

    Parametres
    ----------
    contract_path : chemin absolu vers le .sol temporaire (existe encore)
    issues        : liste des issues normalisees produites par les outils
                    (format : {"tool", "title", "description", "severity",
                               "line", "swcId", "confidence"})

    Retour
    ------
    {
        "verdict":     "vulnerable" | "safe",
        "score":       int (0-100),
        "explanation": str,
        "ai_issues":   list[dict]
    }
    """
    _erreur_fallback = {
        "verdict":     "safe",
        "score":       0,
        "explanation": "",
        "ai_issues":   [],
    }

    if not is_available():
        _erreur_fallback["explanation"] = "Modele GNN non disponible."
        return _erreur_fallback

    # Ecrire les issues dans un fichier temporaire au format attendu par le parser
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix="_rapport_gnn.json", delete=False, encoding="utf-8"
        ) as tmp:
            json.dump(
                {"status": "completed", "report": {"issues": issues}},
                tmp,
                ensure_ascii=False,
            )
            chemin_rapport_tmp = tmp.name
    except Exception as e:
        logger.error(f"[GNN] Erreur creation fichier temporaire : {e}")
        _erreur_fallback["explanation"] = "Erreur interne GNN (fichier temp)."
        return _erreur_fallback

    try:
        resultat_gnn = _gnn_analyser(contract_path, chemin_rapport_tmp)
    except Exception as e:
        logger.error(f"[GNN] Erreur pendant l'analyse : {e}")
        _erreur_fallback["explanation"] = f"Erreur interne GNN : {e}"
        return _erreur_fallback
    finally:
        try:
            os.unlink(chemin_rapport_tmp)
        except OSError:
            pass

    if not resultat_gnn.get("success"):
        erreur = resultat_gnn.get("erreur", "erreur inconnue")
        logger.warning(f"[GNN] Analyse echouee pour {contract_path} : {erreur}")
        _erreur_fallback["explanation"] = f"Analyse GNN impossible : {erreur}"
        return _erreur_fallback

    findings = resultat_gnn.get("findings", [])
    resume   = resultat_gnn.get("resume", {})

    nb_confirmed = resume.get("confirmed", 0)
    nb_potential = resume.get("potential", 0)
    nb_filtered  = resume.get("filtered",  0)

    # -------------------------------------------------------------------
    # ai_issues :
    #   - CONFIRMED : le GNN valide un finding deja produit par un outil.
    #     On le renvoie avec gnn_level="CONFIRMED" pour que scan.py puisse
    #     marquer l'issue existante (confirmedByGnn=True) sans la dupliquer.
    #   - POTENTIAL : le GNN seul a detecte quelque chose. On l'ajoute comme
    #     nouvelle issue (tool="ai").
    # -------------------------------------------------------------------
    ai_issues = []
    for f in findings:
        niveau  = f["niveau"]
        code    = f.get("code", "")
        ligne   = f["lignes"][0] if f.get("lignes") else None
        prob    = f.get("prob_gnn") or 0.0
        titre, swc_id = _titre_et_swc_depuis_code(code)

        if niveau == "CONFIRMED":
            # Renvoye pour marquer l'issue outil existante, PAS pour creer
            # une nouvelle issue dans report.issues.
            ai_issues.append({
                "gnn_level":   "CONFIRMED",
                "tool":        "ai",
                "title":       titre,
                "description": (
                    f"Vulnerabilite confirmee par le GNN ({prob*100:.0f}% de confiance). "
                    f"Le graphe CFG ne contient aucune protection (CEI, nonReentrant, "
                    f"controle d'acces) autour de la ligne {ligne}.\n"
                    f"Code : {code[:120]}"
                ),
                "severity":    _prob_vers_severity(prob),
                "line":        ligne,
                "swcId":       swc_id,
                "confidence":  f"{prob*100:.0f}%",
                "outils":      f.get("outils", []),
            })

        elif niveau == "POTENTIAL":
            ai_issues.append({
                "gnn_level":   "POTENTIAL",
                "tool":        "ai",
                "title":       titre,
                "description": (
                    f"Le modele GNN a detecte une vulnerabilite potentielle "
                    f"({prob*100:.0f}% de confiance) sur la ligne {ligne}.\n"
                    f"Code : {code[:120]}"
                ),
                "severity":    _prob_vers_severity(prob),
                "line":        ligne,
                "swcId":       swc_id,
                "confidence":  f"{prob*100:.0f}%",
            })

    # -------------------------------------------------------------------
    # Verdict
    # -------------------------------------------------------------------
    if nb_confirmed > 0 or nb_potential > 0:
        verdict = "vulnerable"
    else:
        verdict = "safe"

    # -------------------------------------------------------------------
    # Score GNN (0-100, independant du score global)
    # -------------------------------------------------------------------
    max_prob_gnn = max(
        (f["prob_gnn"] for f in findings if f.get("prob_gnn") and f["niveau"] != "FILTERED"),
        default=0.0,
    )
    if nb_confirmed > 0 and max_prob_gnn > 0:
        score = min(100, int(60 + max_prob_gnn * 40))  # 60-100
    elif nb_confirmed > 0:
        score = 65                                       # outil confirme, GNN pas dominant
    elif nb_potential > 0:
        score = min(59, int(30 + max_prob_gnn * 30))    # 30-59
    else:
        score = 0

    # -------------------------------------------------------------------
    # Explication textuelle
    # -------------------------------------------------------------------
    explanation = _generer_explication(
        findings, nb_confirmed, nb_potential, nb_filtered, verdict
    )

    return {
        "verdict":     verdict,
        "score":       score,
        "explanation": explanation,
        "ai_issues":   ai_issues,
    }


# ---------------------------------------------------------------------------
# Utilitaires internes
# ---------------------------------------------------------------------------

_PATTERNS_TITRE = [
    ([".call{", "msg.sender.call", ".call("],     "Unprotected External Call",  "SWC-107"),
    ([".send("],                                   "Unchecked Send",              "SWC-104"),
    ([".transfer("],                               "Unprotected ETH Transfer",    "SWC-105"),
    (["selfdestruct"],                             "Unprotected Selfdestruct",    "SWC-106"),
    (["delegatecall"],                             "Dangerous Delegatecall",      "SWC-112"),
    (["tx.origin"],                                "tx.origin Authentication",    "SWC-115"),
    (["block.timestamp"],                          "Timestamp Dependence",        "SWC-116"),
    (["ecrecover"],                                "Signature Validation Issue",  "SWC-122"),
    (["blockhash", "block.difficulty",
      "block.prevrandao"],                         "Weak Randomness Source",      "SWC-120"),
    (["unchecked"],                                "Unchecked Arithmetic",        "SWC-101"),
    (["swapexacttokens", "swaptokens",
      "latestrounddata"],                          "Oracle/DEX Manipulation",     "SWC-116"),
]


def _titre_et_swc_depuis_code(code: str) -> tuple[str, str]:
    """Infere un titre et un SWC a partir du code du noeud vulnerable."""
    code_lower = code.lower()
    for patterns, titre, swc in _PATTERNS_TITRE:
        if any(p in code_lower for p in patterns):
            return titre, swc
    return "Potential Vulnerability", ""


def _prob_vers_severity(prob: float) -> str:
    if prob >= 0.85:
        return "high"
    if prob >= 0.70:
        return "medium"
    return "low"


def _generer_explication(
    findings: list,
    nb_confirmed: int,
    nb_potential: int,
    nb_filtered: int,
    verdict: str,
) -> str:
    if verdict == "safe":
        if nb_filtered > 0:
            return (
                f"Le contrat semble securise. "
                f"{nb_filtered} alerte(s) detectee(s) par les outils ont ete "
                f"supprimees : la topologie du graphe CFG revele des protections "
                f"(nonReentrant, pattern CEI, controle d'acces proprietaire)."
            )
        return "Le modele GNN ne detecte aucune vulnerabilite structurelle dans ce contrat."

    parties = []

    if nb_confirmed > 0:
        lignes_conf = sorted({
            l for f in findings
            if f["niveau"] == "CONFIRMED"
            for l in f.get("lignes", [])
        })
        lignes_str = ", ".join(str(l) for l in lignes_conf[:5])
        if len(lignes_conf) > 5:
            lignes_str += f" (+ {len(lignes_conf)-5} autres)"
        parties.append(
            f"{nb_confirmed} vulnerabilite(s) confirmee(s) par GNN + outils "
            f"sur la/les ligne(s) {lignes_str}."
        )

    if nb_potential > 0:
        prob_max = max(
            (f["prob_gnn"] for f in findings if f["niveau"] == "POTENTIAL" and f.get("prob_gnn")),
            default=0.0,
        )
        parties.append(
            f"{nb_potential} vulnerabilite(s) potentielle(s) detectee(s) "
            f"uniquement par le GNN (confiance max : {prob_max*100:.0f}%)."
        )

    if nb_filtered > 0:
        parties.append(
            f"{nb_filtered} alerte(s) outil supprimee(s) "
            f"(protection topologique detectee dans le CFG)."
        )

    return " ".join(parties)
