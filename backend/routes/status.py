import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter

from backend.services.control import get_control_state

ROOT_DIR = Path(__file__).resolve().parents[2]
WORKER_STATUS_FILE = ROOT_DIR / "worker_status.json"

router = APIRouter(prefix="/status", tags=["status"])

def _read_status_file() -> dict:
    if not WORKER_STATUS_FILE.exists():
        return {
            "online": False,
            "last_heartbeat": None,
            "hostname": None,
            "current_task_id": None,
            "state": "offline",
        }

    with open(WORKER_STATUS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def get_worker_status_payload() -> dict:
    data = _read_status_file()
    last_heartbeat = data.get("last_heartbeat")
    control = get_control_state()

    online = False
    if last_heartbeat:
        try:
            hb = datetime.fromisoformat(last_heartbeat.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            online = (now - hb).total_seconds() <= 30
        except Exception:
            online = False

    data["online"] = online
    data["agent_paused"] = control.get("paused", False)
    data["stop_requested"] = control.get("stop_requested", False)
    data["stop_task_id"] = control.get("stop_task_id")

    if not online and data.get("state") != "running":
        data["state"] = "offline"

    return data

@router.get("")
def get_status():
    return get_worker_status_payload()