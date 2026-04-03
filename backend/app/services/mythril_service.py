import subprocess
import json
import shutil
import os


def _myth_bin() -> str:
    """Retourne le chemin vers le binaire myth (MYTH_BINARY ou PATH)."""
    return os.environ.get("MYTH_BINARY", "myth")


def is_available() -> bool:
    binary = _myth_bin()
    return os.path.isfile(binary) or shutil.which(binary) is not None


def get_version() -> str:
    try:
        r = subprocess.run([_myth_bin(), "version"], capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or r.stderr.strip()
    except Exception:
        return "?"


def analyze_contract(contract_path: str) -> dict:
    """
    Lance Mythril sur le fichier .sol ou .vy et retourne un dict normalisé.
    Retourne {"issues": [], "error": "..."} si Mythril n'est pas installé.
    """
    if not is_available():
        return {"issues": [], "error": "Mythril non installé (pip install mythril)"}

    command = [_myth_bin(), "analyze", contract_path, "-o", "json"]
    result = subprocess.run(command, capture_output=True, text=True, timeout=300)

    output = result.stdout.strip()

    # Mythril exit codes: 0 = no issues, 1 = issues found OR real error
    if output:
        try:
            raw = json.loads(output)
        except json.JSONDecodeError:
            detail = result.stderr.strip() or output or f"myth exited with code {result.returncode}"
            return {"issues": [], "error": detail}

        issues = []
        for issue in raw.get("issues", []):
            issues.append({
                "title": issue.get("title", ""),
                "description": issue.get("description", ""),
                "severity": issue.get("severity", "Low"),
                "lineno": issue.get("lineno"),
                "swc-id": issue.get("swc-id", ""),
                "tool": "mythril",
                "confidence": "medium",
            })

        return {"issues": issues}

    if result.returncode not in (0, 1):
        detail = result.stderr.strip() or f"myth exited with code {result.returncode}"
        return {"issues": [], "error": detail}

    return {"issues": []}
