from typing import Literal, Optional
from pydantic import BaseModel, Field

AllowedToolName = Literal[
    "take_screenshot",
    "open_url",
    "run_named_script",
    "list_files_in_folder",
]

ControlCommand = Literal[
    "pc_status",
    "pause_agent",
    "resume_agent",
    "queue_status",
    "stop_current_task",
    "latest_status",
    "wake_pc",
]

CodeJobType = Literal[
    "feature",
    "bugfix",
    "refactor",
    "review",
    "continue",
]

CodeRunner = Literal[
    "openai_local",
]

class PlannerDecision(BaseModel):
    decision_type: Literal["task", "control", "code_job"] = Field(
        ...,
        description="Whether this message should execute a task, control action, or coding job."
    )
    reasoning: str = Field(..., description="Why this decision was selected")
    requires_approval: bool = Field(default=False)

    control_command: Optional[ControlCommand] = None

    tool_name: Optional[AllowedToolName] = None
    url: Optional[str] = None
    script_name: Optional[str] = None
    folder_path: Optional[str] = None

    code_job_type: Optional[CodeJobType] = None
    repo_name: Optional[str] = None
    goal: Optional[str] = None
    branch_name: Optional[str] = None
    send_updates: Optional[bool] = True
    runner: Optional[CodeRunner] = None
    subtasks: list[str] = Field(default_factory=list)