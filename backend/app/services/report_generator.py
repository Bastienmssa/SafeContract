"""
backend/app/services/report_generator.py

Génère un rapport d'audit professionnel (Markdown + PDF) à partir du JSON d'analyse.

Dépendances :
    pip install ollama markdown2 weasyprint

Configuration (.env) :
    RAPPORT_LLM_MODEL=mistral          (défaut)
    OLLAMA_HOST=http://localhost:11434  (défaut)
    RAPPORT_LLM_TIMEOUT=120            (secondes)
    RAPPORT_LOGO_PATH=                 (optionnel : PNG/SVG pour la page de garde PDF)

Usage :
    from app.services.report_generator import generer_rapport
    result = generer_rapport(analyse_dict)
    # result["markdown"]  -> str
    # result["pdf_bytes"] -> bytes
"""

import base64
import json
import datetime
import os
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _logo_data_uri() -> Optional[str]:
    """
    Charge le logo SafeContract en data URI pour WeasyPrint (pas de requête réseau).
    Cherche : RAPPORT_LOGO_PATH, puis frontend/public/images/SafeContract-Logo.png.
    """
    candidates: list[str] = []
    env_path = os.environ.get("RAPPORT_LOGO_PATH", "").strip()
    if env_path:
        candidates.append(os.path.expanduser(env_path))

    _services = os.path.dirname(os.path.abspath(__file__))
    _app = os.path.dirname(_services)
    backend_root = os.path.dirname(_app)
    project_root = os.path.dirname(backend_root)
    candidates.append(
        os.path.join(project_root, "frontend", "public", "images", "SafeContract-Logo.png")
    )
    candidates.append(os.path.join(backend_root, "static", "SafeContract-Logo.png"))

    mime_map = {
        ".png": "image/png",
        ".svg": "image/svg+xml",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }

    for path in candidates:
        if not path or not os.path.isfile(path):
            continue
        ext = os.path.splitext(path)[1].lower()
        mime = mime_map.get(ext, "image/png")
        try:
            with open(path, "rb") as f:
                b64 = base64.standard_b64encode(f.read()).decode("ascii")
            return f"data:{mime};base64,{b64}"
        except OSError as e:
            logger.warning("[Rapport] Logo introuvable ou illisible (%s) : %s", path, e)
    return None


def _cover_brand_html() -> str:
    """Bloc marque page de garde : image si disponible, sinon texte stylé."""
    uri = _logo_data_uri()
    if uri:
        return (
            f'<div class="cover-brand">'
            f'<img src="{uri}" alt="SafeContract" class="cover-logo-img"/>'
            f"</div>"
        )
    return (
        '<div class="cover-brand cover-brand--text">'
        '<div class="cover-logo">Safe<span>Contract</span></div>'
        "</div>"
    )


# ---------------------------------------------------------------------------
# Dépendances optionnelles
# ---------------------------------------------------------------------------
try:
    import ollama as _ollama
    _OLLAMA_OK = True
except ImportError:
    _OLLAMA_OK = False
    logger.info("[Rapport] ollama non installé — mode fallback SWC")

try:
    import markdown2 as _md2
    from weasyprint import HTML as _WP_HTML
    _PDF_OK = True
except (ImportError, OSError):
    _PDF_OK = False
    logger.warning("[Rapport] markdown2/weasyprint non disponible (bibliothèques système manquantes) — PDF désactivé")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_MODELE     = os.environ.get("RAPPORT_LLM_MODEL", "mistral")
_TIMEOUT    = int(os.environ.get("RAPPORT_LLM_TIMEOUT", "120"))
_OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

# ---------------------------------------------------------------------------
# Base de connaissances SWC
# ---------------------------------------------------------------------------
_SWC_DB = {
    "SWC-101": {
        "nom":      "Integer Overflow and Underflow",
        "risque":   "Un dépassement arithmétique peut corrompre les soldes ou contourner des conditions de sécurité.",
        "correctif":"Utiliser Solidity ≥ 0.8.0 (overflow natif) ou la bibliothèque SafeMath d'OpenZeppelin.",
        "ref":      "https://swcregistry.io/docs/SWC-101",
    },
    "SWC-104": {
        "nom":      "Unchecked Call Return Value",
        "risque":   "Une valeur de retour non vérifiée peut masquer l'échec d'un transfert de fonds.",
        "correctif":"Toujours vérifier la valeur de retour des appels bas niveau (.call, .send).",
        "ref":      "https://swcregistry.io/docs/SWC-104",
    },
    "SWC-105": {
        "nom":      "Unprotected Ether Withdrawal",
        "risque":   "N'importe quel utilisateur peut retirer les fonds du contrat.",
        "correctif":"Restreindre les fonctions de retrait avec des modificateurs d'accès (onlyOwner).",
        "ref":      "https://swcregistry.io/docs/SWC-105",
    },
    "SWC-106": {
        "nom":      "Unprotected SELFDESTRUCT",
        "risque":   "Un attaquant peut détruire le contrat et récupérer ses fonds.",
        "correctif":"Protéger selfdestruct() avec un contrôle d'accès strict.",
        "ref":      "https://swcregistry.io/docs/SWC-106",
    },
    "SWC-107": {
        "nom":      "Reentrancy",
        "risque":   "Un contrat externe peut réappeler une fonction avant que l'état soit mis à jour, permettant le vol de fonds.",
        "correctif":"Appliquer le pattern Checks-Effects-Interactions (CEI) ou utiliser ReentrancyGuard d'OpenZeppelin.",
        "ref":      "https://swcregistry.io/docs/SWC-107",
    },
    "SWC-112": {
        "nom":      "Delegatecall to Untrusted Callee",
        "risque":   "Un delegatecall vers une adresse non fiable peut compromettre l'état du contrat.",
        "correctif":"Ne jamais effectuer de delegatecall vers une adresse contrôlée par l'utilisateur.",
        "ref":      "https://swcregistry.io/docs/SWC-112",
    },
    "SWC-113": {
        "nom":      "Denial of Service",
        "risque":   "Le contrat peut être rendu inutilisable par un attaquant bloquant les opérations critiques.",
        "correctif":"Utiliser le pattern Pull Payment et éviter les boucles sur des tableaux dynamiques non bornés.",
        "ref":      "https://swcregistry.io/docs/SWC-113",
    },
    "SWC-115": {
        "nom":      "Authorization through tx.origin",
        "risque":   "tx.origin peut être usurpé via une attaque de phishing entre contrats.",
        "correctif":"Remplacer tx.origin par msg.sender pour toute logique d'authentification.",
        "ref":      "https://swcregistry.io/docs/SWC-115",
    },
    "SWC-116": {
        "nom":      "Timestamp Dependence",
        "risque":   "Les mineurs peuvent manipuler block.timestamp de quelques secondes.",
        "correctif":"Ne pas utiliser block.timestamp pour des décisions critiques (tirages, loteries, timelock).",
        "ref":      "https://swcregistry.io/docs/SWC-116",
    },
    "SWC-120": {
        "nom":      "Weak Sources of Randomness",
        "risque":   "Un attaquant peut prédire la valeur pseudo-aléatoire et en tirer profit.",
        "correctif":"Utiliser Chainlink VRF ou un oracle de randomness vérifiable (VRF).",
        "ref":      "https://swcregistry.io/docs/SWC-120",
    },
    "SWC-122": {
        "nom":      "Lack of Proper Signature Verification",
        "risque":   "Une signature peut être rejouée sur une autre transaction ou un autre contrat.",
        "correctif":"Implémenter un nonce par utilisateur et vérifier le domaine (EIP-712 / EIP-191).",
        "ref":      "https://swcregistry.io/docs/SWC-122",
    },
}

_SEV_FR    = {"critical": "CRITIQUE", "high": "ÉLEVÉ", "medium": "MOYEN", "low": "FAIBLE"}
_SEV_COLOR = {"critical": "#dc2626",  "high": "#ea580c", "medium": "#d97706", "low": "#16a34a"}
_SEV_BG    = {"critical": "#fef2f2",  "high": "#fff7ed", "medium": "#fffbeb", "low":  "#f0fdf4"}
_SEV_BORDER= {"critical": "#fca5a5",  "high": "#fdba74", "medium": "#fcd34d", "low":  "#86efac"}
_SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

_TOOL_TYPE = {
    "mythril":  "Analyse symbolique",
    "slither":  "Analyse statique",
    "solhint":  "Analyse statique (lint)",
    "echidna":  "Fuzzing / Test dynamique",
    "foundry":  "Analyse dynamique",
    "ai":       "Intelligence artificielle (GNN)",
}
_TOOL_DESC = {
    "mythril":  "Analyse les chemins d'exécution symbolique du bytecode EVM pour détecter des vulnérabilités de type reentrancy, overflow, etc.",
    "slither":  "Analyseur statique de code source Solidity, détecte les anti-patterns et les bugs courants via des détecteurs spécialisés.",
    "solhint":  "Linter Solidity vérifiant les conventions de style, les bonnes pratiques et les règles de sécurité de base.",
    "echidna":  "Fuzzer de smart contracts basé sur des propriétés, génère des séquences de transactions aléatoires pour trouver des violations.",
    "foundry":  "Framework de test Solidity, exécute des tests de propriétés et des simulations d'attaques sur les contrats.",
    "ai":       "Modèle Graph Neural Network (GNN v6) entraîné sur des smart contracts Solidity, analyse le graphe de flux de contrôle (CFG) avec CodeBERT.",
}


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------
def generer_rapport(analyse: dict) -> dict:
    """
    Génère un rapport d'audit professionnel.

    Paramètre
    ---------
    analyse : dict complet de l'analyse (tel que stocké en MongoDB ou retourné par POST /scan)

    Retour
    ------
    {
        "markdown":  str,           # contenu Markdown téléchargeable
        "pdf_bytes": bytes | None,  # PDF binaire (None si weasyprint absent)
        "erreur":    str | None
    }
    """
    try:
        infos    = _extraire_infos(analyse)
        # Pré-calculer les textes LLM une seule fois pour éviter les doubles appels
        # (_construire_markdown et _construire_html appellent tous les deux le LLM)
        _precalculer_llm(infos)
        markdown = _construire_markdown(infos)
        html     = _construire_html(infos)
        pdf      = _html_vers_pdf(html) if _PDF_OK else None
        return {"markdown": markdown, "pdf_bytes": pdf, "erreur": None}
    except Exception as e:
        logger.exception(f"[Rapport] Erreur génération : {e}")
        return {"markdown": "", "pdf_bytes": None, "erreur": str(e)}


# ---------------------------------------------------------------------------
# Extraction des informations
# ---------------------------------------------------------------------------
def _extraire_infos(analyse: dict) -> dict:
    rapport   = analyse.get("report", analyse)
    issues_brutes = rapport.get("issues", [])

    # Trier par sévérité décroissante
    issues = sorted(
        issues_brutes,
        key=lambda x: _SEV_ORDER.get(x.get("severity", "low"), 3)
    )

    # Enrichir chaque issue avec la base SWC
    for iss in issues:
        swc = iss.get("swcId", "")
        if swc in _SWC_DB:
            iss["_swc_nom"]      = _SWC_DB[swc]["nom"]
            iss["_swc_correctif"]= _SWC_DB[swc]["correctif"]
            iss["_swc_ref"]      = _SWC_DB[swc]["ref"]
        else:
            iss["_swc_nom"]      = ""
            iss["_swc_correctif"]= ""
            iss["_swc_ref"]      = ""

    summary = rapport.get("summary") or {}
    ai_verdict = rapport.get("ai_verdict") or {}

    return {
        "nom_fichier":    analyse.get("filename", "contrat.sol"),
        "score":          rapport.get("score", 0),
        "issues":         issues,
        "nb_critical":    summary.get("critical", 0),
        "nb_medium":      summary.get("medium", 0),
        "nb_low":         summary.get("low", 0),
        "nb_total":       summary.get("total", len(issues)),
        "outils_utilises":rapport.get("tools_used") or [],
        "outils_versions":rapport.get("tools_versions") or {},
        "outils_erreurs": rapport.get("tools_errors") or {},
        "ai_verdict":     ai_verdict,
        "date":           datetime.datetime.now().strftime("%d/%m/%Y"),
        "heure":          datetime.datetime.now().strftime("%H:%M"),
    }


# ---------------------------------------------------------------------------
# LLM — appel avec fallback
# ---------------------------------------------------------------------------
def _appeler_llm(prompt: str, temperature: float = 0.3) -> Optional[str]:
    if not _OLLAMA_OK:
        return None
    try:
        rep = _ollama.chat(
            model=_MODELE,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": temperature},
            timeout=_TIMEOUT,   # ← timeout réellement appliqué
        )
        return rep["message"]["content"].strip()
    except Exception:
        return None


def _precalculer_llm(infos: dict) -> None:
    """
    Calcule tous les textes LLM une seule fois et les stocke dans infos / issues.
    Les fonctions _llm_* lisent le cache en priorité → pas de double appel LLM
    entre _construire_markdown et _construire_html.
    """
    _llm_resume_executif(infos)           # remplit infos["_resume_cache"]
    for iss in infos["issues"]:
        _llm_detail_finding(iss)          # remplit iss["_detail_cache"]


def _llm_resume_executif(infos: dict) -> str:
    """Génère le résumé exécutif via LLM, ou utilise un template statique."""
    if "_resume_cache" in infos:
        return infos["_resume_cache"]
    nb_c = infos["nb_critical"]
    nb_m = infos["nb_medium"]
    nb_l = infos["nb_low"]
    score = infos["score"]
    nom = infos["nom_fichier"]
    swcs = list({i.get("swcId","") for i in infos["issues"] if i.get("swcId")})
    ai_expl = infos["ai_verdict"].get("explanation", "")

    prompt = f"""Tu es un auditeur de sécurité blockchain expert. Rédige un résumé exécutif professionnel en français pour un rapport d'audit.

Contrat analysé : {nom}
Score de risque : {score}/100
Résultats : {nb_c} vulnérabilité(s) critique(s), {nb_m} moyenne(s), {nb_l} faible(s)
SWC détectés : {', '.join(swcs) if swcs else 'Aucun'}
Analyse IA : {ai_expl}

Contraintes :
- 3 paragraphes maximum
- Pas de formatage Markdown (texte brut)
- Ton professionnel et factuel
- Conclure par une recommandation claire (déployer ou ne pas déployer)
"""
    texte = _appeler_llm(prompt)
    if texte:
        infos["_resume_cache"] = texte
        return texte

    # Fallback statique
    if nb_c > 0:
        verdict = f"**Ce contrat ne doit pas être déployé** en l'état. {nb_c} vulnérabilité(s) critique(s) exposent directement les fonds des utilisateurs."
    elif nb_m > 0:
        verdict = f"Ce contrat présente {nb_m} vulnérabilité(s) de sévérité moyenne nécessitant une correction avant déploiement."
    else:
        verdict = "Ce contrat ne présente pas de vulnérabilité majeure. Une revue manuelle complémentaire est recommandée avant déploiement."

    result = (
        f"L'audit de sécurité du contrat **{nom}** a été réalisé le {infos['date']} "
        f"à l'aide d'une analyse combinant des outils statiques, dynamiques et un modèle IA (GNN). "
        f"Le score de risque calculé est de **{score}/100**.\n\n"
        f"{nb_c} vulnérabilité(s) critique(s), {nb_m} moyenne(s) et {nb_l} faible(s) ont été identifiées "
        f"sur un total de {infos['nb_total']} findings.\n\n"
        f"{verdict}"
    )
    infos["_resume_cache"] = result
    return result


def _llm_detail_finding(finding: dict) -> dict:
    """Génère l'explication détaillée d'un finding via LLM."""
    if "_detail_cache" in finding:
        return finding["_detail_cache"]
    titre    = finding.get("title", "Vulnérabilité")
    desc     = finding.get("description", "")
    sev      = finding.get("severity", "medium")
    ligne    = finding.get("line")
    swc      = finding.get("swcId", "")
    outil    = finding.get("tool", "")
    gnn_desc = finding.get("gnnDescription", finding.get("description", ""))
    swc_info = _SWC_DB.get(swc, {})

    prompt = f"""Tu es un auditeur de sécurité blockchain. Explique cette vulnérabilité Solidity en français.

Titre : {titre}
SWC : {swc} ({swc_info.get('nom', '')})
Sévérité : {sev}
Ligne : {ligne}
Outil : {outil}
Description : {desc}
Analyse GNN : {gnn_desc}

Réponds UNIQUEMENT avec ce format (sans Markdown, texte brut) :
EXPLICATION: (2 phrases max expliquant la faille concrètement)
IMPACT: (1 phrase sur la conséquence pour les fonds/utilisateurs)
RECOMMANDATION: (correctif Solidity précis, 2 phrases max)
"""
    texte = _appeler_llm(prompt, temperature=0.2)

    explication   = ""
    impact        = ""
    recommandation = swc_info.get("correctif", "Consulter le registre SWC pour les meilleures pratiques.")

    if texte:
        for ligne_txt in texte.split("\n"):
            if ligne_txt.startswith("EXPLICATION:"):
                explication = ligne_txt.replace("EXPLICATION:", "").strip()
            elif ligne_txt.startswith("IMPACT:"):
                impact = ligne_txt.replace("IMPACT:", "").strip()
            elif ligne_txt.startswith("RECOMMANDATION:"):
                recommandation = ligne_txt.replace("RECOMMANDATION:", "").strip()

    # Fallback depuis base SWC
    if not explication:
        explication = swc_info.get("risque", desc[:200] if desc else "Voir description ci-dessus.")
    if not impact:
        impact = "Risque de perte de fonds ou de compromission du contrat."

    result = {
        "explication":    explication,
        "impact":         impact,
        "recommandation": recommandation,
    }
    finding["_detail_cache"] = result
    return result


# ---------------------------------------------------------------------------
# Construction Markdown
# ---------------------------------------------------------------------------
def _construire_markdown(infos: dict) -> str:
    lignes = []

    # En-tête
    lignes += [
        f"# Rapport d'audit de sécurité — {infos['nom_fichier']}",
        f"",
        f"> **Date :** {infos['date']} à {infos['heure']}  ",
        f"> **Score de risque global :** {infos['score']}/100  ",
        f"> **Verdict IA :** {infos['ai_verdict'].get('verdict', 'N/A').upper()}  ",
        f"> **Outils :** {', '.join(infos['outils_utilises'])}",
        f"",
        "---",
        "",
    ]

    # Résumé exécutif
    lignes += [
        "## 1. Résumé exécutif",
        "",
        _llm_resume_executif(infos),
        "",
        "---",
        "",
    ]

    # Tableau de synthèse
    lignes += [
        "## 2. Synthèse des vulnérabilités",
        "",
        f"| Sévérité | Nombre |",
        f"|----------|--------|",
        f"| 🔴 Critique | {infos['nb_critical']} |",
        f"| 🟡 Moyen   | {infos['nb_medium']} |",
        f"| 🟢 Faible  | {infos['nb_low']} |",
        f"| **Total**  | **{infos['nb_total']}** |",
        "",
        "---",
        "",
    ]

    # Findings détaillés
    lignes += [
        "## 3. Findings détaillés",
        "",
    ]

    for idx, finding in enumerate(infos["issues"], 1):
        sev       = finding.get("severity", "low")
        sev_fr    = _SEV_FR.get(sev, sev.upper())
        titre     = finding.get("title", "Vulnérabilité")
        ligne_sol = finding.get("line")
        swc       = finding.get("swcId", "")
        outil     = finding.get("tool", "").upper()
        confirme  = finding.get("confirmedByGnn", False)
        gnn_conf  = finding.get("gnnConfidence", "")

        detail = _llm_detail_finding(finding)

        badge_gnn = f" · ✅ GNN {gnn_conf}" if confirme else ""
        badge_swc = f" · [{swc}]({_SWC_DB.get(swc, {}).get('ref', '#')})" if swc else ""

        lignes += [
            f"### {idx}. [{sev_fr}] {titre}",
            f"",
            f"**Outil :** {outil}{badge_gnn}{badge_swc}  ",
            f"**Ligne :** {ligne_sol if ligne_sol else 'N/A'}  ",
            f"**Sévérité :** {sev_fr}  ",
            f"",
            f"**Explication**",
            f"> {detail['explication']}",
            f"",
            f"**Impact**",
            f"> {detail['impact']}",
            f"",
            f"**Recommandation**",
            f"> {detail['recommandation']}",
            f"",
        ]

        # Bloc GNN si présent
        if finding.get("gnnDescription"):
            gnn_desc = finding["gnnDescription"].replace("\n", "  \n> ")
            lignes += [
                f"**Analyse GNN**",
                f"> {gnn_desc}",
                f"",
            ]

        lignes.append("---")
        lignes.append("")

    # Méthodologie
    lignes += [
        "## 4. Méthodologie",
        "",
        "L'analyse a été conduite en combinant les approches suivantes :",
        "",
        "| Outil | Type | Version |",
        "|-------|------|---------|",
    ]
    for outil, version in infos["outils_versions"].items():
        lignes.append(f"| {outil.capitalize()} | {'Symbolique' if outil=='mythril' else 'Statique' if outil in ('slither','solhint') else 'Dynamique' if outil in ('echidna','foundry') else 'IA GNN'} | {version} |")

    if infos["outils_erreurs"]:
        lignes += [
            "",
            "**Outils non exécutés :**",
            "",
        ]
        for outil, err in infos["outils_erreurs"].items():
            lignes.append(f"- **{outil}** : {err}")

    lignes += [
        "",
        "---",
        "",
        "## 5. Avertissement légal",
        "",
        "> Ce rapport est produit automatiquement par SafeContract. Il ne constitue pas un audit "
        "de sécurité manuel complet et ne saurait engager la responsabilité de ses auteurs. "
        "Un audit humain complémentaire est fortement recommandé avant tout déploiement en production.",
        "",
        "---",
        f"*Rapport généré le {infos['date']} à {infos['heure']} — SafeContract Audit Platform*",
    ]

    return "\n".join(lignes)


# ---------------------------------------------------------------------------
# Construction HTML (pour PDF)
# ---------------------------------------------------------------------------
def _construire_html(infos: dict) -> str:
    """Génère un HTML paginé pour WeasyPrint avec couverture pleine page, sommaire,
    avertissement, explication du scoring, détail des outils et findings.
    Les tableaux et cartes de findings ne sont jamais coupés entre deux pages.
    """

    def badge(sev: str) -> str:
        c  = _SEV_COLOR.get(sev, "#6b7280")
        bg = _SEV_BG.get(sev, "#f9fafb")
        bd = _SEV_BORDER.get(sev, "#d1d5db")
        label = _SEV_FR.get(sev, sev.upper())
        return (
            f'<span style="background:{bg};color:{c};border:1px solid {bd};'
            f'padding:2px 10px;border-radius:4px;font-size:11px;font-weight:700;'
            f'white-space:nowrap;">{label}</span>'
        )

    def section_title(num: int, text: str) -> str:
        return (
            f'<h2 style="font-size:17px;font-weight:700;color:#0f172a;'
            f'border-bottom:2px solid #e2e8f0;padding-bottom:10px;'
            f'margin:0 0 20px 0;page-break-after:avoid;">'
            f'<span style="color:#2cbe88;margin-right:8px;">{num}.</span>{text}</h2>'
        )

    resume      = _llm_resume_executif(infos)
    score       = infos["score"]
    score_color = "#16a34a" if score >= 70 else "#d97706" if score >= 40 else "#dc2626"
    verdict_ai  = infos["ai_verdict"].get("verdict", "N/A").upper()
    verdict_color = "#dc2626" if verdict_ai == "VULNERABLE" else "#16a34a"
    cover_brand = _cover_brand_html()

    # ── Sommaire ──────────────────────────────────────────────────────────────
    toc_items = [
        ("1", "Résumé exécutif"),
        ("2", "Avertissement sur la fiabilité"),
        ("3", "Méthode de calcul du score"),
        ("4", "Outils utilisés"),
        ("5", "Tableau de synthèse"),
        ("6", "Findings détaillés"),
    ]
    toc_rows = "".join(
        f'<tr><td style="padding:6px 0;color:#374151;font-size:13px;">'
        f'<span style="color:#2cbe88;font-weight:600;margin-right:10px;">{n}.</span>{t}</td>'
        f'<td style="text-align:right;color:#94a3b8;font-size:12px;padding:6px 0;">'
        f'{"·" * 30}</td></tr>'
        for n, t in toc_items
    )

    # ── Statistiques ──────────────────────────────────────────────────────────
    stats_html = f"""
    <div style="display:flex;gap:14px;margin-bottom:24px;page-break-inside:avoid;">
      <div style="flex:1;background:#fef2f2;border:1px solid #fca5a5;border-radius:8px;padding:16px;text-align:center;">
        <div style="font-size:30px;font-weight:700;color:#dc2626;">{infos['nb_critical']}</div>
        <div style="font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#dc2626;margin-top:4px;">Critique</div>
      </div>
      <div style="flex:1;background:#fffbeb;border:1px solid #fcd34d;border-radius:8px;padding:16px;text-align:center;">
        <div style="font-size:30px;font-weight:700;color:#d97706;">{infos['nb_medium']}</div>
        <div style="font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#d97706;margin-top:4px;">Moyen</div>
      </div>
      <div style="flex:1;background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:16px;text-align:center;">
        <div style="font-size:30px;font-weight:700;color:#16a34a;">{infos['nb_low']}</div>
        <div style="font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#16a34a;margin-top:4px;">Faible</div>
      </div>
      <div style="flex:1;background:#f1f5f9;border:1px solid #cbd5e1;border-radius:8px;padding:16px;text-align:center;">
        <div style="font-size:30px;font-weight:700;color:#475569;">{infos['nb_total']}</div>
        <div style="font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#475569;margin-top:4px;">Total</div>
      </div>
    </div>"""

    # ── Tableau de synthèse ───────────────────────────────────────────────────
    rows_synth = ""
    for f in infos["issues"]:
        sev = f.get("severity", "low")
        gnn_cell = (
            f'<span style="color:#16a34a;font-weight:600;">✓ {f.get("gnnConfidence","")}</span>'
            if f.get("confirmedByGnn") else
            '<span style="color:#94a3b8;">—</span>'
        )
        rows_synth += (
            f'<tr>'
            f'<td>{badge(sev)}</td>'
            f'<td style="font-weight:600;color:#111827;">{f.get("title","")}</td>'
            f'<td style="text-align:center;color:#6b7280;">{f.get("line") or "—"}</td>'
            f'<td style="color:#6b7280;">{f.get("tool","").capitalize()}</td>'
            f'<td style="color:#6b7280;font-family:monospace;font-size:11px;">{f.get("swcId","") or "—"}</td>'
            f'<td style="text-align:center;">{gnn_cell}</td>'
            f'</tr>'
        )

    synth_table = f"""
    <div style="page-break-inside:avoid;">
      <table style="width:100%;border-collapse:collapse;font-size:13px;">
        <thead>
          <tr style="background:#0f172a;">
            <th style="color:#e2e8f0;text-align:left;padding:10px 12px;font-size:11px;text-transform:uppercase;letter-spacing:.04em;">Sévérité</th>
            <th style="color:#e2e8f0;text-align:left;padding:10px 12px;font-size:11px;text-transform:uppercase;letter-spacing:.04em;">Titre</th>
            <th style="color:#e2e8f0;text-align:center;padding:10px 12px;font-size:11px;text-transform:uppercase;letter-spacing:.04em;">Ligne</th>
            <th style="color:#e2e8f0;text-align:left;padding:10px 12px;font-size:11px;text-transform:uppercase;letter-spacing:.04em;">Outil</th>
            <th style="color:#e2e8f0;text-align:left;padding:10px 12px;font-size:11px;text-transform:uppercase;letter-spacing:.04em;">SWC</th>
            <th style="color:#e2e8f0;text-align:center;padding:10px 12px;font-size:11px;text-transform:uppercase;letter-spacing:.04em;">GNN</th>
          </tr>
        </thead>
        <tbody>{rows_synth}</tbody>
      </table>
    </div>"""

    # ── Findings détaillés ────────────────────────────────────────────────────
    findings_html = ""
    for idx, finding in enumerate(infos["issues"], 1):
        sev      = finding.get("severity", "low")
        detail   = _llm_detail_finding(finding)
        swc      = finding.get("swcId", "")
        swc_info = _SWC_DB.get(swc, {})
        c        = _SEV_COLOR.get(sev, "#6b7280")
        bg       = _SEV_BG.get(sev, "#f9fafb")
        bd       = _SEV_BORDER.get(sev, "#d1d5db")

        swc_link = ""
        if swc and swc_info.get("ref"):
            swc_link = (
                f'<span style="font-family:monospace;font-size:11px;'
                f'background:#f1f5f9;border:1px solid #e2e8f0;'
                f'padding:1px 6px;border-radius:3px;color:#475569;">{swc}</span>'
            )

        gnn_section = ""
        if finding.get("gnnDescription"):
            gnn_section = (
                f'<div style="background:#f0f9ff;border-left:3px solid #0ea5e9;'
                f'padding:10px 14px;margin-top:12px;border-radius:0 4px 4px 0;">'
                f'<p style="margin:0 0 4px;font-size:11px;font-weight:700;'
                f'text-transform:uppercase;letter-spacing:.04em;color:#0369a1;">Analyse GNN</p>'
                f'<p style="margin:0;font-size:13px;color:#0c4a6e;">'
                f'{finding["gnnDescription"].replace(chr(10),"<br>")}</p>'
                f'</div>'
            )

        findings_html += f"""
        <div style="background:#fff;border:1px solid {bd};border-left:4px solid {c};
                    border-radius:6px;padding:20px 22px;margin-bottom:18px;
                    page-break-inside:avoid;">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;
                      gap:12px;margin-bottom:14px;flex-wrap:wrap;">
            <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
              <span style="font-size:14px;font-weight:700;color:#111827;">{idx}. {finding.get('title','')}</span>
              {badge(sev)}
              {swc_link}
            </div>
            <div style="font-size:12px;color:#94a3b8;">
              Outil : <strong style="color:#475569;">{finding.get('tool','').capitalize()}</strong>
              &nbsp;·&nbsp; Ligne : <strong style="color:#475569;">{finding.get('line') or '—'}</strong>
              {'&nbsp;·&nbsp;<span style="color:#16a34a;font-weight:600;">GNN ✓ ' + str(finding.get("gnnConfidence","")) + '</span>' if finding.get("confirmedByGnn") else ''}
            </div>
          </div>

          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;">
            <div style="background:#f8fafc;border-radius:4px;padding:12px;">
              <p style="margin:0 0 5px;font-size:11px;font-weight:700;text-transform:uppercase;
                        letter-spacing:.04em;color:#64748b;">Explication</p>
              <p style="margin:0;font-size:13px;color:#374151;line-height:1.55;">{detail['explication']}</p>
            </div>
            <div style="background:#f8fafc;border-radius:4px;padding:12px;">
              <p style="margin:0 0 5px;font-size:11px;font-weight:700;text-transform:uppercase;
                        letter-spacing:.04em;color:#64748b;">Impact</p>
              <p style="margin:0;font-size:13px;color:#374151;line-height:1.55;">{detail['impact']}</p>
            </div>
          </div>

          <div style="background:#f0fdf4;border-left:3px solid #16a34a;
                      padding:10px 14px;border-radius:0 4px 4px 0;">
            <p style="margin:0 0 4px;font-size:11px;font-weight:700;text-transform:uppercase;
                      letter-spacing:.04em;color:#15803d;">Recommandation</p>
            <p style="margin:0;font-size:13px;color:#166534;line-height:1.55;">{detail['recommandation']}</p>
          </div>
          {gnn_section}
        </div>"""

    # ── Outils utilisés ───────────────────────────────────────────────────────
    rows_outils = ""
    for outil, version in infos["outils_versions"].items():
        type_outil = _TOOL_TYPE.get(outil, "Analyse")
        desc_outil = _TOOL_DESC.get(outil, "")
        rows_outils += (
            f'<tr>'
            f'<td style="font-weight:600;color:#111827;white-space:nowrap;">{outil.capitalize()}</td>'
            f'<td style="color:#475569;">{type_outil}</td>'
            f'<td style="font-family:monospace;font-size:12px;color:#6b7280;white-space:nowrap;">{version}</td>'
            f'<td style="color:#64748b;font-size:12px;">{desc_outil}</td>'
            f'</tr>'
        )

    erreurs_html = ""
    if infos["outils_erreurs"]:
        items = "".join(
            f'<li style="margin-bottom:4px;"><strong>{o}</strong> : '
            f'<span style="color:#6b7280;">{e}</span></li>'
            for o, e in infos["outils_erreurs"].items()
        )
        erreurs_html = (
            f'<div style="margin-top:14px;background:#fff7ed;border:1px solid #fed7aa;'
            f'border-radius:6px;padding:12px 16px;">'
            f'<p style="margin:0 0 6px;font-size:12px;font-weight:700;color:#92400e;">'
            f'Outils non exécutés</p>'
            f'<ul style="margin:0;padding-left:16px;font-size:13px;">{items}</ul>'
            f'</div>'
        )

    outils_table = f"""
    <div style="page-break-inside:avoid;">
      <table style="width:100%;border-collapse:collapse;font-size:13px;">
        <thead>
          <tr style="background:#0f172a;">
            <th style="color:#e2e8f0;text-align:left;padding:10px 12px;font-size:11px;text-transform:uppercase;letter-spacing:.04em;white-space:nowrap;">Outil</th>
            <th style="color:#e2e8f0;text-align:left;padding:10px 12px;font-size:11px;text-transform:uppercase;letter-spacing:.04em;">Type</th>
            <th style="color:#e2e8f0;text-align:left;padding:10px 12px;font-size:11px;text-transform:uppercase;letter-spacing:.04em;">Version</th>
            <th style="color:#e2e8f0;text-align:left;padding:10px 12px;font-size:11px;text-transform:uppercase;letter-spacing:.04em;">Description</th>
          </tr>
        </thead>
        <tbody>{rows_outils}</tbody>
      </table>
      {erreurs_html}
    </div>"""

    # ── HTML complet ──────────────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<style>
  /* ── Mise en page WeasyPrint ── */
  @page {{
    size: A4;
    margin: 2cm 2cm 2.2cm 2cm;
    @bottom-center {{
      content: "Page " counter(page) " / " counter(pages);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      font-size: 10px;
      color: #94a3b8;
    }}
    @bottom-left {{
      content: "SafeContract — Rapport d'audit";
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      font-size: 10px;
      color: #94a3b8;
    }}
    @bottom-right {{
      content: "{infos['date']}";
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      font-size: 10px;
      color: #94a3b8;
    }}
  }}

  /* Couverture : pleine page sans marges */
  @page cover {{
    margin: 0;
    @bottom-center {{ content: none; }}
    @bottom-left   {{ content: none; }}
    @bottom-right  {{ content: none; }}
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    color: #111827;
    font-size: 14px;
    line-height: 1.65;
  }}

  /* ── Couverture ── */
  .cover {{
    page: cover;
    page-break-after: always;
    background: linear-gradient(160deg, #0a1628 0%, #0f2040 45%, #091628 100%);
    color: #fff;
    width: 100%;
    height: 100vh;
    min-height: 297mm;
    display: flex;
    flex-direction: column;
    padding: 52px 56px 48px;
  }}
  .cover-brand {{ margin-bottom: 0; flex: 1; display: flex; align-items: flex-start; }}
  .cover-logo-img {{ max-height: 52px; max-width: 240px; width: auto; height: auto; object-fit: contain; display: block; }}
  .cover-brand--text .cover-logo {{ font-size: 22px; font-weight: 700; letter-spacing: -0.5px; }}
  .cover-logo span {{ color: #2cbe88; }}

  .cover-body {{ flex: 2; display: flex; flex-direction: column; justify-content: center; padding: 40px 0; }}
  .cover-eyebrow {{ font-size: 12px; text-transform: uppercase; letter-spacing: .12em; color: #2cbe88; font-weight: 600; margin-bottom: 16px; }}
  .cover-title {{ font-size: 38px; font-weight: 700; line-height: 1.15; margin-bottom: 12px; color: #fff; }}
  .cover-filename {{
    font-size: 18px; color: rgba(255,255,255,.6); margin-bottom: 48px;
    font-family: "SF Mono", "Fira Code", monospace;
  }}

  .cover-kpis {{ display: flex; gap: 24px; flex-wrap: wrap; }}
  .kpi {{
    background: rgba(255,255,255,.07);
    border: 1px solid rgba(255,255,255,.12);
    border-radius: 10px;
    padding: 18px 24px;
    min-width: 130px;
  }}
  .kpi-label {{ font-size: 11px; text-transform: uppercase; letter-spacing: .06em; color: rgba(255,255,255,.5); margin-bottom: 8px; }}
  .kpi-value {{ font-size: 26px; font-weight: 700; }}

  .cover-footer {{
    font-size: 12px; color: rgba(255,255,255,.35);
    border-top: 1px solid rgba(255,255,255,.1);
    padding-top: 20px;
    display: flex;
    justify-content: space-between;
  }}

  /* ── Sections de contenu ── */
  .section {{ page-break-before: always; padding-top: 4px; }}
  .section:first-child {{ page-break-before: avoid; }}

  h2 {{
    font-size: 17px; font-weight: 700; color: #0f172a;
    border-bottom: 2px solid #e2e8f0; padding-bottom: 10px;
    margin: 0 0 20px 0;
    page-break-after: avoid;
  }}
  h2 .section-num {{ color: #2cbe88; margin-right: 8px; }}

  p {{ color: #374151; margin-bottom: 10px; line-height: 1.65; }}

  /* ── Tableaux ── */
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  thead tr {{ background: #0f172a; }}
  thead th {{
    color: #e2e8f0; text-align: left; padding: 10px 12px;
    font-size: 11px; text-transform: uppercase; letter-spacing: .04em;
  }}
  tbody td {{ padding: 10px 12px; border-bottom: 1px solid #f1f5f9; color: #374151; vertical-align: top; }}
  tbody tr:last-child td {{ border-bottom: none; }}
  tbody tr:nth-child(even) {{ background: #f8fafc; }}

  /* Interdire la coupure de tableaux et de findings */
  .no-break {{ page-break-inside: avoid; }}

  /* ── Sommaire ── */
  .toc-table {{ width: 100%; border-collapse: collapse; }}
  .toc-table td {{ padding: 6px 0; border-bottom: 1px dotted #e2e8f0; }}
  .toc-table tr:last-child td {{ border-bottom: none; }}

  /* ── Avertissement ── */
  .warning-box {{
    background: #fffbeb;
    border: 1px solid #fcd34d;
    border-left: 4px solid #f59e0b;
    border-radius: 6px;
    padding: 16px 20px;
    page-break-inside: avoid;
  }}

  /* ── Score info ── */
  .score-explain {{
    background: #f0f9ff;
    border: 1px solid #bae6fd;
    border-left: 4px solid #0ea5e9;
    border-radius: 6px;
    padding: 16px 20px;
    page-break-inside: avoid;
  }}
  .penalty-grid {{ display: flex; gap: 14px; margin-top: 14px; flex-wrap: wrap; }}
  .penalty-item {{
    flex: 1; min-width: 100px;
    text-align: center; border-radius: 6px;
    padding: 12px;
  }}
  .penalty-num {{ font-size: 22px; font-weight: 700; }}
  .penalty-lbl {{ font-size: 11px; text-transform: uppercase; letter-spacing: .04em; margin-top: 4px; }}
</style>
</head>
<body>

<!-- ═══════════════════════════════════ COUVERTURE ═══════════════════════════════════ -->
<div class="cover">
  <div class="cover-brand">
    {cover_brand}
  </div>

  <div class="cover-body">
    <div class="cover-eyebrow">Rapport d&apos;audit de sécurité</div>
    <div class="cover-title">Smart Contract<br>Security Audit</div>
    <div class="cover-filename">{infos['nom_fichier']}</div>

    <div class="cover-kpis">
      <div class="kpi">
        <div class="kpi-label">Score de sécurité</div>
        <div class="kpi-value" style="color:{score_color};">{score}<span style="font-size:14px;font-weight:400;color:rgba(255,255,255,.4);">/100</span></div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Verdict IA</div>
        <div class="kpi-value" style="color:{verdict_color};font-size:18px;">{verdict_ai}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Findings</div>
        <div class="kpi-value" style="color:rgba(255,255,255,.9);">{infos['nb_total']}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Critique</div>
        <div class="kpi-value" style="color:#f87171;">{infos['nb_critical']}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Date</div>
        <div class="kpi-value" style="font-size:16px;color:rgba(255,255,255,.8);">{infos['date']}</div>
      </div>
    </div>
  </div>

  <div class="cover-footer">
    <span>SafeContract Audit Platform</span>
    <span>Généré le {infos['date']} à {infos['heure']}</span>
    <span>Confidentiel</span>
  </div>
</div>

<!-- ═══════════════════════════════════ SOMMAIRE ═══════════════════════════════════ -->
<div class="section no-break">
  <h2><span class="section-num">—</span>Sommaire</h2>
  <table class="toc-table">
    <tbody>
      {"".join(
        f'<tr><td style="color:#374151;font-size:13px;padding:8px 0;">'
        f'<span style="color:#2cbe88;font-weight:700;margin-right:10px;">{n}.</span>{t}</td></tr>'
        for n, t in toc_items
      )}
    </tbody>
  </table>
</div>

<!-- ═══════════════════════════════════ 1. RÉSUMÉ ════════════════════════════════════ -->
<div class="section">
  <h2><span class="section-num">1.</span>Résumé exécutif</h2>
  <p>{resume.replace(chr(10), '</p><p>')}</p>
  {stats_html}
</div>

<!-- ════════════════════════════════ 2. AVERTISSEMENT ═══════════════════════════════ -->
<div class="section no-break">
  <h2><span class="section-num">2.</span>Avertissement sur la fiabilité</h2>
  <div class="warning-box">
    <p style="margin:0 0 10px;font-weight:700;color:#92400e;font-size:14px;">
      ⚠ Ce rapport est produit par des outils automatisés
    </p>
    <p style="margin:0 0 8px;font-size:13px;color:#78350f;">
      L&apos;analyse de SafeContract combine plusieurs moteurs d&apos;analyse statique, dynamique et un modèle
      d&apos;intelligence artificielle (GNN). Ces outils offrent une couverture étendue mais ne garantissent
      pas l&apos;absence totale de vulnérabilités.
    </p>
    <ul style="margin:0;padding-left:18px;font-size:13px;color:#78350f;line-height:1.7;">
      <li>Les faux positifs sont possibles : vérifiez chaque finding manuellement.</li>
      <li>Les faux négatifs existent : des vulnérabilités logiques complexes (erreurs de conception)
          peuvent ne pas être détectées automatiquement.</li>
      <li>Ce rapport ne remplace pas un audit de sécurité humain complet.</li>
      <li>SafeContract et ses auteurs déclinent toute responsabilité en cas de perte résultant
          d&apos;un déploiement basé uniquement sur ce rapport.</li>
    </ul>
    <p style="margin:12px 0 0;font-size:13px;font-weight:600;color:#92400e;">
      Un audit manuel par un expert blockchain est fortement recommandé avant tout déploiement
      en production, particulièrement si des fonds utilisateurs sont en jeu.
    </p>
  </div>
</div>

<!-- ═══════════════════════════════ 3. CALCUL DU SCORE ══════════════════════════════ -->
<div class="section no-break">
  <h2><span class="section-num">3.</span>Méthode de calcul du score</h2>
  <div class="score-explain">
    <p style="margin:0 0 10px;font-size:13px;color:#0c4a6e;">
      Le <strong>score de sécurité</strong> est calculé sur 100 points. Il part de 100 et des pénalités
      sont appliquées pour chaque vulnérabilité détectée. Le score minimum est 0.
    </p>
    <div class="penalty-grid">
      <div class="penalty-item" style="background:#fef2f2;border:1px solid #fca5a5;">
        <div class="penalty-num" style="color:#dc2626;">−30</div>
        <div class="penalty-lbl" style="color:#dc2626;">par Critique</div>
      </div>
      <div class="penalty-item" style="background:#fffbeb;border:1px solid #fcd34d;">
        <div class="penalty-num" style="color:#d97706;">−15</div>
        <div class="penalty-lbl" style="color:#d97706;">par Moyen</div>
      </div>
      <div class="penalty-item" style="background:#f0fdf4;border:1px solid #86efac;">
        <div class="penalty-num" style="color:#16a34a;">−5</div>
        <div class="penalty-lbl" style="color:#16a34a;">par Faible</div>
      </div>
    </div>
    <p style="margin:14px 0 0;font-size:12px;color:#0369a1;">
      <strong>Pondération GNN :</strong> lorsque le modèle GNN confirme une vulnérabilité détectée
      par un outil, la pénalité est multipliée par 1,5 (ex. : une critique confirmée par le GNN
      retire 45 points au lieu de 30). Cela reflète la plus haute fiabilité du verdict croisé
      outil + IA.
    </p>
    <p style="margin:10px 0 0;font-size:12px;color:#0369a1;">
      <strong>Score obtenu pour ce contrat :</strong>
      <span style="font-size:15px;font-weight:700;color:{score_color};margin-left:6px;">{score}/100</span>
      &nbsp;—&nbsp;
      <span style="color:#475569;">{"Sûr" if score >= 80 else "Risque modéré" if score >= 50 else "Critique"}</span>
    </p>
  </div>
</div>

<!-- ══════════════════════════════ 4. OUTILS UTILISÉS ═══════════════════════════════ -->
<div class="section">
  <h2><span class="section-num">4.</span>Outils utilisés</h2>
  {outils_table}
</div>

<!-- ══════════════════════════════ 5. TABLEAU DE SYNTHÈSE ═══════════════════════════ -->
<div class="section">
  <h2><span class="section-num">5.</span>Tableau de synthèse</h2>
  {synth_table}
</div>

<!-- ══════════════════════════════ 6. FINDINGS DÉTAILLÉS ════════════════════════════ -->
<div class="section">
  <h2><span class="section-num">6.</span>Findings détaillés</h2>
  {findings_html if findings_html else '<p style="color:#64748b;font-style:italic;">Aucune vulnérabilité détectée.</p>'}
</div>

</body>
</html>"""

    return html


def _html_vers_pdf(html: str) -> Optional[bytes]:
    if not _PDF_OK:
        return None
    try:
        return _WP_HTML(string=html).write_pdf()
    except Exception as e:
        logger.error(f"[Rapport] Erreur PDF : {e}")
        return None
