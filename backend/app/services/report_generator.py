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
_SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


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
    """Génère un HTML stylé directement (meilleur contrôle que Markdown → HTML)."""

    def badge(sev):
        c = _SEV_COLOR.get(sev, "#6b7280")
        bg = _SEV_BG.get(sev, "#f9fafb")
        return f'<span style="background:{bg};color:{c};border:1px solid {c};padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700;">{_SEV_FR.get(sev, sev.upper())}</span>'

    resume = _llm_resume_executif(infos)

    # --- Lignes de findings ---
    rows_table = ""
    for f in infos["issues"]:
        sev = f.get("severity", "low")
        rows_table += f"""
        <tr>
          <td>{badge(sev)}</td>
          <td style="font-weight:600;">{f.get('title','')}</td>
          <td style="text-align:center;">{f.get('line') or '—'}</td>
          <td>{f.get('tool','').upper()}</td>
          <td>{f.get('swcId','') or '—'}</td>
          <td style="text-align:center;">{'✅' if f.get('confirmedByGnn') else '—'}</td>
        </tr>"""

    # --- Sections findings ---
    sections_findings = ""
    for idx, finding in enumerate(infos["issues"], 1):
        sev    = finding.get("severity", "low")
        detail = _llm_detail_finding(finding)
        swc    = finding.get("swcId", "")
        swc_info = _SWC_DB.get(swc, {})
        gnn_html = ""
        if finding.get("gnnDescription"):
            gnn_html = f"""
            <div style="background:#f0f9ff;border-left:3px solid #0ea5e9;padding:10px 14px;margin-top:12px;border-radius:4px;">
              <strong style="color:#0369a1;">Analyse GNN</strong><br>
              <span style="font-size:13px;">{finding['gnnDescription'].replace(chr(10),'<br>')}</span>
            </div>"""

        swc_badge = ""
        if swc and swc_info.get("ref"):
            swc_badge = f' &nbsp;<a href="{swc_info["ref"]}" style="font-size:11px;color:#6b7280;">[{swc}]</a>'

        sections_findings += f"""
        <div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:20px 24px;margin-bottom:20px;">
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;">
            <span style="font-size:15px;font-weight:700;color:#111827;">{idx}. {finding.get('title','')}</span>
            {badge(sev)}{swc_badge}
          </div>
          <table style="font-size:12px;color:#6b7280;border-collapse:collapse;margin-bottom:12px;">
            <tr>
              <td style="padding-right:20px;"><strong>Outil</strong> : {finding.get('tool','').upper()}</td>
              <td style="padding-right:20px;"><strong>Ligne</strong> : {finding.get('line') or '—'}</td>
              {'<td><strong>GNN</strong> : ✅ ' + str(finding.get("gnnConfidence","")) + '</td>' if finding.get("confirmedByGnn") else ''}
            </tr>
          </table>
          <div style="margin-bottom:10px;">
            <p style="margin:0 0 4px;font-weight:600;color:#374151;">Explication</p>
            <p style="margin:0;font-size:14px;color:#4b5563;">{detail['explication']}</p>
          </div>
          <div style="margin-bottom:10px;">
            <p style="margin:0 0 4px;font-weight:600;color:#374151;">Impact</p>
            <p style="margin:0;font-size:14px;color:#4b5563;">{detail['impact']}</p>
          </div>
          <div style="background:#f0fdf4;border-left:3px solid #16a34a;padding:10px 14px;border-radius:4px;">
            <p style="margin:0 0 4px;font-weight:600;color:#15803d;">Recommandation</p>
            <p style="margin:0;font-size:14px;color:#166534;">{detail['recommandation']}</p>
          </div>
          {gnn_html}
        </div>"""

    # --- Tableau méthodologie ---
    rows_methodo = ""
    for outil, version in infos["outils_versions"].items():
        type_outil = (
            "Analyse symbolique" if outil == "mythril" else
            "Analyse statique"   if outil in ("slither", "solhint") else
            "Analyse dynamique"  if outil in ("echidna", "foundry") else
            "Intelligence artificielle (GNN)"
        )
        rows_methodo += f"<tr><td>{outil.capitalize()}</td><td>{type_outil}</td><td>{version}</td></tr>"

    erreurs_methodo = ""
    for outil, err in infos["outils_erreurs"].items():
        erreurs_methodo += f"<li><strong>{outil}</strong> : {err}</li>"
    if erreurs_methodo:
        erreurs_methodo = f"<p style='margin-top:12px;font-size:13px;color:#6b7280;'><strong>Outils non exécutés :</strong></p><ul style='font-size:13px;color:#6b7280;'>{erreurs_methodo}</ul>"

    score = infos["score"]
    # score = score de sécurité (100 = sûr, 0 = critique) → vert si élevé, rouge si bas
    score_color = "#16a34a" if score >= 70 else "#d97706" if score >= 40 else "#dc2626"
    verdict_ai = infos["ai_verdict"].get("verdict", "N/A").upper()
    verdict_color = "#dc2626" if verdict_ai == "VULNERABLE" else "#16a34a"

    cover_brand = _cover_brand_html()

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; color: #111827; background: #f9fafb; font-size: 14px; line-height: 1.6; }}
  .page {{ max-width: 900px; margin: 0 auto; background: #fff; }}

  /* Cover */
  .cover {{ background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%); color: #fff; padding: 48px 50px 50px; }}
  .cover-brand {{ display: flex; align-items: flex-start; justify-content: flex-start; margin-bottom: 48px; }}
  .cover-logo-img {{ max-height: 56px; max-width: 260px; width: auto; height: auto; object-fit: contain; display: block; }}
  .cover-brand--text .cover-logo {{ font-size: 22px; font-weight: 700; letter-spacing: -0.5px; opacity: 0.95; margin-bottom: 0; }}
  .cover-logo span {{ color: #38bdf8; }}
  .cover-title {{ font-size: 32px; font-weight: 700; line-height: 1.2; margin-bottom: 8px; }}
  .cover-subtitle {{ font-size: 16px; opacity: 0.7; margin-bottom: 40px; }}
  .cover-meta {{ display: flex; gap: 40px; margin-top: 30px; }}
  .cover-meta-item label {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; opacity: 0.6; display: block; margin-bottom: 4px; }}
  .cover-meta-item value {{ font-size: 15px; font-weight: 600; }}
  .score-badge {{ display: inline-block; background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.3); border-radius: 8px; padding: 8px 16px; font-size: 28px; font-weight: 700; color: {score_color}; }}

  /* Sections */
  .content {{ padding: 40px 50px; }}
  h2 {{ font-size: 18px; font-weight: 700; color: #0f172a; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px; margin: 32px 0 18px; }}
  h2:first-child {{ margin-top: 0; }}
  p {{ color: #374151; margin-bottom: 12px; }}

  /* Tables */
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 16px; }}
  th {{ background: #f1f5f9; color: #475569; text-align: left; padding: 10px 12px; font-size: 12px; text-transform: uppercase; letter-spacing: 0.03em; }}
  td {{ padding: 10px 12px; border-bottom: 1px solid #f1f5f9; color: #374151; }}
  tr:last-child td {{ border-bottom: none; }}

  /* Résumé chiffres */
  .stats-row {{ display: flex; gap: 16px; margin-bottom: 24px; }}
  .stat-card {{ flex: 1; border-radius: 8px; padding: 16px; text-align: center; }}
  .stat-card .num {{ font-size: 28px; font-weight: 700; }}
  .stat-card .lbl {{ font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; opacity: 0.8; margin-top: 4px; }}
  .stat-critical {{ background: #fef2f2; color: #dc2626; }}
  .stat-medium   {{ background: #fffbeb; color: #d97706; }}
  .stat-low      {{ background: #f0fdf4; color: #16a34a; }}
  .stat-total    {{ background: #f1f5f9; color: #475569; }}

  /* Disclaimer */
  .disclaimer {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px 20px; font-size: 12px; color: #64748b; margin-top: 32px; }}
  .footer {{ text-align: center; font-size: 11px; color: #94a3b8; padding: 20px; border-top: 1px solid #e5e7eb; margin-top: 20px; }}
</style>
</head>
<body>
<div class="page">

  <!-- COVER -->
  <div class="cover">
    {cover_brand}
    <div class="cover-title">Rapport d'audit de sécurité</div>
    <div class="cover-subtitle">{infos['nom_fichier']}</div>
    <div class="cover-meta">
      <div class="cover-meta-item">
        <label>Score de risque</label>
        <div class="score-badge">{score}/100</div>
      </div>
      <div class="cover-meta-item">
        <label>Verdict IA</label>
        <value style="color:{verdict_color};">{verdict_ai}</value>
      </div>
      <div class="cover-meta-item">
        <label>Date</label>
        <value>{infos['date']}</value>
      </div>
      <div class="cover-meta-item">
        <label>Findings</label>
        <value>{infos['nb_total']} détectés</value>
      </div>
    </div>
  </div>

  <div class="content">

    <!-- RÉSUMÉ EXÉCUTIF -->
    <h2>1. Résumé exécutif</h2>
    <p>{resume.replace(chr(10), '</p><p>')}</p>

    <!-- STATISTIQUES -->
    <div class="stats-row" style="margin-top:20px;">
      <div class="stat-card stat-critical"><div class="num">{infos['nb_critical']}</div><div class="lbl">Critique</div></div>
      <div class="stat-card stat-medium"><div class="num">{infos['nb_medium']}</div><div class="lbl">Moyen</div></div>
      <div class="stat-card stat-low"><div class="num">{infos['nb_low']}</div><div class="lbl">Faible</div></div>
      <div class="stat-card stat-total"><div class="num">{infos['nb_total']}</div><div class="lbl">Total</div></div>
    </div>

    <!-- TABLEAU SYNTHÈSE -->
    <h2>2. Tableau de synthèse</h2>
    <table>
      <thead>
        <tr><th>Sévérité</th><th>Titre</th><th>Ligne</th><th>Outil</th><th>SWC</th><th>GNN</th></tr>
      </thead>
      <tbody>{rows_table}</tbody>
    </table>

    <!-- FINDINGS DÉTAILLÉS -->
    <h2>3. Findings détaillés</h2>
    {sections_findings}

    <!-- MÉTHODOLOGIE -->
    <h2>4. Méthodologie</h2>
    <table>
      <thead><tr><th>Outil</th><th>Type d'analyse</th><th>Version</th></tr></thead>
      <tbody>{rows_methodo}</tbody>
    </table>
    {erreurs_methodo}

    <!-- DISCLAIMER -->
    <div class="disclaimer">
      <strong>Avertissement légal</strong><br>
      Ce rapport est produit automatiquement par SafeContract. Il ne constitue pas un audit de sécurité
      manuel complet et ne saurait engager la responsabilité de ses auteurs. Un audit humain
      complémentaire est fortement recommandé avant tout déploiement en production.
    </div>

  </div>
  <div class="footer">Rapport généré le {infos['date']} à {infos['heure']} — SafeContract Audit Platform</div>
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
