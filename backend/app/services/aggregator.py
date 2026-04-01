"""
aggregator.py
Normalise et fusionne les résultats de tous les outils d'analyse
(Mythril, Slither, Solhint, Echidna, Foundry) en un format JSON unifié.
"""
from __future__ import annotations
from typing import Any


# ─── Normalisation de la sévérité ────────────────────────────────────────────

_SEVERITY_MAP = {
    "high":          "critical",
    "medium":        "medium",
    "low":           "low",
    "critical":      "critical",
    "informational": "low",
    "optimization":  "low",
}


def _normalize_severity(raw: str) -> str:
    return _SEVERITY_MAP.get(raw.lower(), "low")


# ─── Normalisation d'une issue individuelle ──────────────────────────────────

def _normalize_issue(issue: dict, tool: str) -> dict:
    severity_raw = issue.get("severity", "low")
    if tool == "mythril":
        severity = _normalize_severity(severity_raw)
    else:
        severity = severity_raw

    return {
        "tool": issue.get("tool", tool),
        "title": issue.get("title", ""),
        "description": issue.get("description") or issue.get("desc", ""),
        "severity": severity,
        "line": issue.get("lineno") or issue.get("line"),
        "swcId": (
            f"SWC-{issue['swc-id']}" if issue.get("swc-id") else issue.get("swcId", "")
        ),
        "confidence": issue.get("confidence", ""),
    }


# ─── Calcul du score de sécurité ─────────────────────────────────────────────

def compute_score(issues: list[dict]) -> int:
    criticals = sum(1 for i in issues if i["severity"] == "critical")
    mediums = sum(1 for i in issues if i["severity"] == "medium")
    lows = sum(1 for i in issues if i["severity"] == "low")
    return max(0, min(100, 100 - criticals * 25 - mediums * 10 - lows * 5))


# ─── Déduplication ───────────────────────────────────────────────────────────

def _deduplicate(issues: list[dict]) -> list[dict]:
    severity_order = {"critical": 3, "medium": 2, "low": 1}
    seen: dict[tuple, dict] = {}

    for issue in issues:
        key = (issue["title"].lower()[:60], issue["line"])
        if key not in seen:
            seen[key] = issue
        else:
            existing_level = severity_order.get(seen[key]["severity"], 0)
            new_level = severity_order.get(issue["severity"], 0)
            if new_level > existing_level:
                seen[key] = issue

    return list(seen.values())


# ─── Fonction principale ──────────────────────────────────────────────────────

def aggregate(tool_results: dict[str, Any]) -> dict:
    all_issues: list[dict] = []
    tools_used: list[str] = []
    tools_errors: dict[str, str] = {}

    for tool, result in tool_results.items():
        if result is None:
            continue

        error = result.get("error")
        raw_issues = result.get("issues", [])
        if not isinstance(raw_issues, list):
            raw_issues = []

        # Outil en erreur sans aucune issue → non disponible, ne pas compter comme utilisé
        if error and not raw_issues:
            tools_errors[tool] = error
            continue

        # Outil en erreur partielle (a quand même remonté des issues)
        if error:
            tools_errors[tool] = error

        tools_used.append(tool)

        for raw in raw_issues:
            all_issues.append(_normalize_issue(raw, tool))

    unique_issues = _deduplicate(all_issues)

    severity_order = {"critical": 0, "medium": 1, "low": 2}
    unique_issues.sort(key=lambda i: severity_order.get(i["severity"], 3))

    score = compute_score(unique_issues)

    summary = {
        "critical": sum(1 for i in unique_issues if i["severity"] == "critical"),
        "medium": sum(1 for i in unique_issues if i["severity"] == "medium"),
        "low": sum(1 for i in unique_issues if i["severity"] == "low"),
        "total": len(unique_issues),
    }

    return {
        "score": score,
        "issues": unique_issues,
        "tools_used": tools_used,
        "tools_errors": tools_errors,
        "summary": summary,
    }
