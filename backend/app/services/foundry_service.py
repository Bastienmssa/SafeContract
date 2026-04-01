import subprocess
import json
import shutil
import os
import tempfile


def get_version() -> str:
    import re
    try:
        r = subprocess.run(["forge", "--version"], capture_output=True, text=True, timeout=10)
        output = r.stdout.strip() or r.stderr.strip()
        m = re.search(r'(\d+\.\d+\.\d+(?:-\w+)?)', output)
        return m.group(1) if m else output
    except Exception:
        return "?"


def is_available() -> bool:
    return shutil.which("forge") is not None


def analyze_contract(contract_path: str) -> dict:
    """
    Compile le contrat via Foundry (forge build) et détecte les erreurs de compilation
    et les avertissements de sécurité remontés par le compilateur Solidity.
    """
    if not contract_path.endswith(".sol"):
        return {"issues": [], "error": "Foundry ne supporte que les fichiers .sol"}

    if not is_available():
        return {"issues": [], "error": "Foundry non installé (https://getfoundry.sh)"}

    with tempfile.TemporaryDirectory() as tmpdir:
        src_dir = os.path.join(tmpdir, "src")
        os.makedirs(src_dir)

        contract_name = os.path.basename(contract_path)
        dest_path = os.path.join(src_dir, contract_name)
        with open(contract_path, "r") as f:
            content = f.read()
        with open(dest_path, "w") as f:
            f.write(content)

        foundry_toml = os.path.join(tmpdir, "foundry.toml")
        with open(foundry_toml, "w") as f:
            f.write("[profile.default]\nsrc = 'src'\nout = 'out'\nlibs = ['lib']\n")

        command = ["forge", "build", "--json"]
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, cwd=tmpdir, timeout=120
            )
        except subprocess.TimeoutExpired:
            return {"issues": [], "error": "forge build timeout (> 120s)"}

        output = result.stdout.strip()
        stderr = result.stderr.strip()
        issues = []

        if output:
            try:
                raw = json.loads(output)
                for _contract_key, contract_data in raw.get("contracts", {}).items():
                    for warning in contract_data.get("warnings", []):
                        issues.append({
                            "title": f"Compiler warning: {warning.get('errorCode', 'unknown')}",
                            "description": warning.get("formattedMessage", warning.get("message", "")),
                            "severity": "low",
                            "lineno": (
                                warning.get("sourceLocation", {}).get("start")
                                if warning.get("sourceLocation") else None
                            ),
                            "swc-id": "",
                            "tool": "foundry",
                            "confidence": "high",
                        })
            except json.JSONDecodeError:
                pass

        if result.returncode != 0 and stderr:
            for line in stderr.splitlines():
                line = line.strip()
                if line.startswith("Error") or "error" in line.lower():
                    issues.append({
                        "title": "Erreur de compilation Foundry",
                        "description": line,
                        "severity": "high",
                        "lineno": None,
                        "swc-id": "",
                        "tool": "foundry",
                        "confidence": "high",
                    })

        return {"issues": issues}
