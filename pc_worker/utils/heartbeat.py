import json
import socket
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
WORKER_STATUS_FILE = ROOT_DIR / "worker_status.json"

def write_heartbeat(current_task_id: str | None = None, state: str = "idle") -> None:
    payload = {
        "last_heartbeat": datetime.now(timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
        "current_task_id": current_task_id,
        "state": state,
    }

    with open(WORKER_STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

def mark_worker_offline() -> None:
    payload = {
        "last_heartbeat": datetime.now(timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
        "current_task_id": None,
        "state": "offline",
    }

    with open(WORKER_STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)