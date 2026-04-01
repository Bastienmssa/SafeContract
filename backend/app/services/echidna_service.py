import subprocess
import json
import shutil
import os
import tempfile


def get_version() -> str:
    try:
        binary = "echidna" if shutil.which("echidna") else "echidna-test"
        r = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or r.stderr.strip()
    except Exception:
        return "?"


def is_available() -> bool:
    return shutil.which("echidna") is not None or shutil.which("echidna-test") is not None


def _get_binary() -> str:
    if shutil.which("echidna"):
        return "echidna"
    return "echidna-test"


def analyze_contract(contract_path: str) -> dict:
    """
    Lance Echidna en mode fuzzing sur le contrat Solidity.
    Echidna cherche des propriétés violées (fonctions débutant par 'echidna_').
    Si aucune propriété n'est présente, retourne un avertissement.
    Echidna ne supporte pas Vyper nativement.
    """
    if not contract_path.endswith(".sol"):
        return {"issues": [], "error": "Echidna ne supporte que les fichiers .sol"}

    if not is_available():
        return {"issues": [], "error": "Echidna non installé (https://github.com/crytic/echidna)"}

    binary = _get_binary()

    config = {
        "testMode": "assertion",
        "testLimit": 50000,
        "timeout": 60,
        "format": "json",
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as cfg_file:
        import yaml
        yaml.dump(config, cfg_file)
        cfg_path = cfg_file.name

    command = [binary, contract_path, "--config", cfg_path, "--format", "json"]

    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return {"issues": [], "error": "Echidna timeout (> 120s)"}
    finally:
        os.unlink(cfg_path)

    output = result.stdout.strip()
    if not output:
        return {"issues": []}

    try:
        raw = json.loads(output)
    except json.JSONDecodeError:
        return {
            "issues": [],
            "info": "Aucune propriété echidna_ trouvée — ajoutez des fonctions echidna_* pour le fuzzing",
        }

    issues = []
    for test in raw if isinstance(raw, list) else raw.get("tests", []):
        if test.get("status") == "failed":
            issues.append({
                "title": f"Propriété violée : {test.get('name', 'unknown')}",
                "description": (
                    f"Echidna a trouvé un contre-exemple pour {test.get('name')}. "
                    f"Séquence : {json.dumps(test.get('reproducer', []))}"
                ),
                "severity": "high",
                "lineno": None,
                "swc-id": "",
                "tool": "echidna",
                "confidence": "high",
            })

    return {"issues": issues}
