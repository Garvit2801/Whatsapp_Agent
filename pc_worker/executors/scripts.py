import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]

ALLOWED_SCRIPTS = {
    "daily_report": ROOT_DIR / "scripts" / "daily_report.py",
    "cleanup_downloads": ROOT_DIR / "scripts" / "cleanup_downloads.py",
    "stock_report": ROOT_DIR / "scripts" / "stock_report.py",
}

def run_named_script(script_name: str) -> dict:
    script_path = ALLOWED_SCRIPTS.get(script_name)
    if not script_path:
        return {"success": False, "message": f"Script not allowed: {script_name}"}

    if not script_path.exists():
        return {"success": False, "message": f"Script file not found: {script_path}"}

    try:
        result = subprocess.run(
            ["python", str(script_path)],
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            return {
                "success": False,
                "message": f"Script failed with exit code {result.returncode}",
                "stdout": result.stdout[-2000:],
                "stderr": result.stderr[-2000:],
            }

        return {
            "success": True,
            "message": f"Script executed successfully: {script_name}",
            "stdout": result.stdout[-2000:],
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": f"Script timed out: {script_name}",
        }