import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from shared.config import TASKS_FILE, RESULTS_FILE

def _ensure_file(path: str):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump([], f)

def load_json(path: str) -> List[Dict[str, Any]]:
    _ensure_file(path)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: str, data: List[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def enqueue_task(task: Dict[str, Any]) -> None:
    tasks = load_json(TASKS_FILE)
    tasks.append(task)
    save_json(TASKS_FILE, tasks)

def get_all_tasks() -> List[Dict[str, Any]]:
    return load_json(TASKS_FILE)

def get_task_by_id(task_id: str) -> Optional[Dict[str, Any]]:
    tasks = load_json(TASKS_FILE)
    for task in tasks:
        if task["id"] == task_id:
            return task
    return None

def get_last_task_for_number(from_number: str) -> Optional[Dict[str, Any]]:
    tasks = load_json(TASKS_FILE)
    user_tasks = [t for t in tasks if t.get("from_number") == from_number]
    if not user_tasks:
        return None
    return sorted(user_tasks, key=lambda x: x.get("created_at", ""), reverse=True)[0]

def get_waiting_approval_tasks_for_number(from_number: str) -> List[Dict[str, Any]]:
    tasks = load_json(TASKS_FILE)
    pending = [
        t for t in tasks
        if t.get("from_number") == from_number and t.get("status") == "waiting_approval"
    ]
    return sorted(pending, key=lambda x: x.get("created_at", ""))

def get_waiting_approval_task_by_serial(from_number: str, serial_number: int) -> Optional[Dict[str, Any]]:
    waiting = get_waiting_approval_tasks_for_number(from_number)
    if serial_number < 1 or serial_number > len(waiting):
        return None
    return waiting[serial_number - 1]

def get_pending_tasks() -> List[Dict[str, Any]]:
    tasks = load_json(TASKS_FILE)
    return [t for t in tasks if t["status"] == "pending"]

def get_queue_summary(limit: int = 10) -> List[Dict[str, Any]]:
    tasks = load_json(TASKS_FILE)
    queued = [t for t in tasks if t["status"] in {"pending", "waiting_approval", "running"}]
    return sorted(queued, key=lambda x: x.get("created_at", ""))[:limit]

def get_current_running_task() -> Optional[Dict[str, Any]]:
    tasks = load_json(TASKS_FILE)
    running = [t for t in tasks if t["status"] == "running"]
    if not running:
        return None
    return sorted(running, key=lambda x: x.get("updated_at", ""), reverse=True)[0]

def set_task_status(task_id: str, status: str) -> None:
    tasks = load_json(TASKS_FILE)
    for t in tasks:
        if t["id"] == task_id:
            t["status"] = status
            t["updated_at"] = datetime.utcnow().isoformat()
    save_json(TASKS_FILE, tasks)

def set_task_running(task_id: str) -> None:
    set_task_status(task_id, "running")

def set_task_waiting_approval(task_id: str) -> None:
    tasks = load_json(TASKS_FILE)
    for t in tasks:
        if t["id"] == task_id:
            t["status"] = "waiting_approval"
            t["approval_status"] = "pending"
            t["updated_at"] = datetime.utcnow().isoformat()
    save_json(TASKS_FILE, tasks)

def approve_task(task_id: str) -> Optional[Dict[str, Any]]:
    tasks = load_json(TASKS_FILE)
    approved_task = None
    for t in tasks:
        if t["id"] == task_id:
            t["status"] = "pending"
            t["approval_status"] = "approved"
            t["updated_at"] = datetime.utcnow().isoformat()
            approved_task = t
    save_json(TASKS_FILE, tasks)
    return approved_task

def reject_task(task_id: str) -> Optional[Dict[str, Any]]:
    tasks = load_json(TASKS_FILE)
    rejected_task = None
    for t in tasks:
        if t["id"] == task_id:
            t["status"] = "cancelled"
            t["approval_status"] = "rejected"
            t["updated_at"] = datetime.utcnow().isoformat()
            rejected_task = t
    save_json(TASKS_FILE, tasks)
    return rejected_task

def cancel_task(task_id: str, reason: str = "Cancelled by user") -> Optional[Dict[str, Any]]:
    tasks = load_json(TASKS_FILE)
    cancelled_task = None
    result = {
        "success": False,
        "message": reason,
        "finished_at": datetime.utcnow().isoformat(),
        "extra": {"cancelled": True},
    }

    for t in tasks:
        if t["id"] == task_id and t["status"] in {"pending", "waiting_approval", "running"}:
            t["status"] = "cancelled"
            t["updated_at"] = datetime.utcnow().isoformat()
            t["result"] = result
            cancelled_task = t

    save_json(TASKS_FILE, tasks)

    if cancelled_task:
        results = load_json(RESULTS_FILE)
        results.append({"task_id": task_id, **result})
        save_json(RESULTS_FILE, results)

    return cancelled_task

def mark_task_done(task_id: str, result: Dict[str, Any]) -> None:
    tasks = load_json(TASKS_FILE)
    for t in tasks:
        if t["id"] == task_id:
            t["status"] = "done"
            t["result"] = result
            t["updated_at"] = datetime.utcnow().isoformat()
    save_json(TASKS_FILE, tasks)

    results = load_json(RESULTS_FILE)
    results.append({"task_id": task_id, **result})
    save_json(RESULTS_FILE, results)

def mark_task_failed(task_id: str, error_message: str, extra: Optional[Dict[str, Any]] = None) -> None:
    extra = extra or {}
    result = {
        "success": False,
        "message": error_message,
        "finished_at": datetime.utcnow().isoformat(),
        "extra": extra,
    }

    tasks = load_json(TASKS_FILE)
    for t in tasks:
        if t["id"] == task_id:
            t["status"] = "failed"
            t["result"] = result
            t["updated_at"] = datetime.utcnow().isoformat()
    save_json(TASKS_FILE, tasks)

    results = load_json(RESULTS_FILE)
    results.append({"task_id": task_id, **result})
    save_json(RESULTS_FILE, results)

def get_recent_tasks(limit: int = 10) -> List[Dict[str, Any]]:
    tasks = load_json(TASKS_FILE)
    return sorted(tasks, key=lambda x: x.get("created_at", ""), reverse=True)[:limit]