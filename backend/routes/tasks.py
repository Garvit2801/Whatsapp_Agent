from fastapi import APIRouter, HTTPException

from backend.services.dispatcher import get_recent_tasks, get_task_by_id

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("")
def list_tasks(limit: int = 10):
    return {"tasks": get_recent_tasks(limit=limit)}

@router.get("/{task_id}")
def get_task(task_id: str):
    task = get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task