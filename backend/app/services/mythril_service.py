import subprocess
import json


def analyze_contract(contract_path: str):

    command = [
        "myth",
        "analyze",
        contract_path,
        "-o",
        "json"
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    output = result.stdout.strip()

    # Mythril exit codes: 0 = no issues, 1 = issues found OR real error
    # Distinguish by checking if stdout is valid JSON
    if output:
        try:
            report = json.loads(output)
            return report
        except json.JSONDecodeError:
            pass

    # If we reach here, stdout was not valid JSON — it's a real error
    detail = result.stderr.strip() or output or f"myth exited with code {result.returncode}"
    raise Exception(detail)