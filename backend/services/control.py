import json
import os
from datetime import datetime, timezone

from shared.config import AGENT_CONTROL_FILE

DEFAULT_CONTROL_STATE = {
    "paused": False,
    "stop_requested": False,
    "stop_task_id": None,
    "updated_at": None,
}

def _ensure_file():
    if not os.path.exists(AGENT_CONTROL_FILE):
        with open(AGENT_CONTROL_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONTROL_STATE, f, indent=2)

def get_control_state() -> dict:
    _ensure_file()
    with open(AGENT_CONTROL_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _write_state(state: dict) -> None:
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(AGENT_CONTROL_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

def set_paused(paused: bool) -> dict:
    state = get_control_state()
    state["paused"] = paused
    _write_state(state)
    return state

def request_stop(task_id: str | None = None) -> dict:
    state = get_control_state()
    state["stop_requested"] = True
    state["stop_task_id"] = task_id
    _write_state(state)
    return state

def clear_stop_request() -> dict:
    state = get_control_state()
    state["stop_requested"] = False
    state["stop_task_id"] = None
    _write_state(state)
    return state