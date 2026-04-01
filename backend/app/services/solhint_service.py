import subprocess
import json
import shutil


def get_version() -> str:
    try:
        r = subprocess.run(["solhint", "--version"], capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or r.stderr.strip()
    except Exception:
        return "?"


def is_available() -> bool:
    return shutil.which("solhint") is not None


def analyze_contract(contract_path: str) -> dict:
    """
    Lance Solhint sur le fichier .sol et retourne un dict normalisé.
    Solhint ne supporte que Solidity (pas Vyper).
    """
    if not contract_path.endswith(".sol"):
        return {"issues": [], "error": "Solhint ne supporte que les fichiers .sol"}

    if not is_available():
        return {"issues": [], "error": "Solhint non installé (npm install -g solhint)"}

    command = ["solhint", "--formatter", "json", contract_path]
    result = subprocess.run(command, capture_output=True, text=True)

    output = result.stdout.strip()
    if not output:
        return {"issues": []}

    try:
        raw = json.loads(output)
    except json.JSONDecodeError:
        return {"issues": [], "error": f"Sortie Solhint non-JSON: {output[:200]}"}

    issues = []
    for file_report in raw if isinstance(raw, list) else []:
        for msg in file_report.get("messages", []):
            severity_code = msg.get("severity", 1)
            severity = "medium" if severity_code == 2 else "low"
            issues.append({
                "title": msg.get("ruleId", "solhint-rule"),
                "description": msg.get("message", ""),
                "severity": severity,
                "lineno": msg.get("line"),
                "swc-id": "",
                "tool": "solhint",
                "confidence": "high",
            })

    return {"issues": issues}
