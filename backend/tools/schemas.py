from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class TaskCreate(BaseModel):
    id: str
    created_at: str
    from_number: str
    to_number: str
    raw_command: str
    status: str = "pending"
    tool_name: str
    reasoning: str
    requires_approval: bool = False
    approval_status: str = "not_required"
    args: Dict[str, Any] = Field(default_factory=dict)

class TaskResult(BaseModel):
    task_id: str
    success: bool
    message: str
    artifact_path: Optional[str] = None
    finished_at: str
    extra: Dict[str, Any] = Field(default_factory=dict)