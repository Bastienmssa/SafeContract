import subprocess
import json
import shutil


def get_version() -> str:
    try:
        r = subprocess.run(["slither", "--version"], capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or r.stderr.strip()
    except Exception:
        return "?"


def is_available() -> bool:
    return shutil.which("slither") is not None


def analyze_contract(contract_path: str) -> dict:
    """
    Lance Slither sur le fichier .sol ou .vy et retourne un dict normalisé.
    Retourne {"issues": [], "error": "..."} si Slither n'est pas installé.
    """
    if not is_available():
        return {"issues": [], "error": "Slither non installé (pip install slither-analyzer)"}

    command = [
        "slither",
        contract_path,
        "--json", "-",
        "--no-fail-pedantic",
    ]

    result = subprocess.run(command, capture_output=True, text=True)

    output = result.stdout.strip()
    if not output:
        stderr = result.stderr.strip()
        if result.returncode not in (0, 1):
            return {"issues": [], "error": stderr or f"slither exited with code {result.returncode}"}
        return {"issues": []}

    try:
        raw = json.loads(output)
    except json.JSONDecodeError:
        return {"issues": [], "error": f"Sortie Slither non-JSON: {output[:200]}"}

    issues = []
    for detector in raw.get("results", {}).get("detectors", []):
        impact = detector.get("impact", "Informational").lower()
        if impact in ("high", "critical"):
            severity = "high"
        elif impact == "medium":
            severity = "medium"
        else:
            severity = "low"

        elements = detector.get("elements", [])
        lineno = None
        for el in elements:
            src = el.get("source_mapping", {})
            if src.get("lines"):
                lineno = src["lines"][0]
                break

        issues.append({
            "title": detector.get("check", "Unknown check"),
            "description": detector.get("description", ""),
            "severity": severity,
            "lineno": lineno,
            "swc-id": "",
            "tool": "slither",
            "confidence": detector.get("confidence", ""),
        })

    return {"issues": issues}
