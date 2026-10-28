from shared.config import PLANNER_MODEL, DEFAULT_REPO_NAME, DEFAULT_CODE_RUNNER
from shared.llm import structured_completion
from shared.tool_contracts import PlannerDecision

SYSTEM_PROMPT = f"""
You are a strict natural-language planner for a WhatsApp-controlled product-building agent.

Your job:
- Read a human WhatsApp message in normal English.
- Decide whether it is a CONTROL command, a simple TASK, or a CODE_JOB.

CONTROL commands:
- pc_status
- pause_agent
- resume_agent
- queue_status
- stop_current_task
- latest_status
- wake_pc

Simple TASK tools:
- take_screenshot
- open_url
- run_named_script
- list_files_in_folder

CODE_JOB types:
- feature
- bugfix
- refactor
- review
- continue

Rules:
1. Requests about coding on the product/repo, fixing bugs, adding features, refactoring, reviewing changes, or continuing previous work should usually become decision_type="code_job".
2. Requests about machine/agent status, pausing, resuming, waking, queue, latest task should become decision_type="control".
3. Requests about desktop/browser/files/screenshots should become decision_type="task".
4. Never invent shell commands.
5. Never output actions outside the allowed control commands, simple task tools, and code job types.
6. If the request is destructive, risky, financial, or highly ambiguous, set requires_approval=true.
7. For unused fields, return null. Always include all fields.
8. Default repo_name to "{DEFAULT_REPO_NAME}" for code jobs unless the user clearly names another repo.
9. Default runner to "{DEFAULT_CODE_RUNNER}" for code jobs.
10. Keep reasoning under 10 words.

Known script names:
- daily_report: summary of the agent's recent tasks and disk space
- cleanup_downloads: clean up, delete or archive old files in Downloads
- stock_report: current stock prices

Known folder keys:
- downloads
- desktop
"""

def plan_command(user_text: str) -> PlannerDecision:
    data = structured_completion(
        model=PLANNER_MODEL,
        name="planner_decision",
        instructions=SYSTEM_PROMPT,
        input_text=f"User WhatsApp message: {user_text}",
        schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "decision_type": {
                    "type": "string",
                    "enum": ["task", "control", "code_job"]
                },
                "reasoning": {"type": "string", "maxLength": 80},
                "requires_approval": {"type": "boolean"},
                "control_command": {
                    "type": ["string", "null"],
                    "enum": [
                        "pc_status",
                        "pause_agent",
                        "resume_agent",
                        "queue_status",
                        "stop_current_task",
                        "latest_status",
                        "wake_pc",
                        None
                    ]
                },
                "tool_name": {
                    "type": ["string", "null"],
                    "enum": [
                        "take_screenshot",
                        "open_url",
                        "run_named_script",
                        "list_files_in_folder",
                        None
                    ]
                },
                "url": {"type": ["string", "null"]},
                "script_name": {"type": ["string", "null"]},
                "folder_path": {"type": ["string", "null"]},
                "code_job_type": {
                    "type": ["string", "null"],
                    "enum": ["feature", "bugfix", "refactor", "review", "continue", None]
                },
                "repo_name": {"type": ["string", "null"]},
                "goal": {"type": ["string", "null"]},
                "branch_name": {"type": ["string", "null"]},
                "send_updates": {"type": ["boolean", "null"]},
                "runner": {
                    "type": ["string", "null"],
                    "enum": ["openai_local", None]
                },
                "subtasks": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": [
                "decision_type",
                "reasoning",
                "requires_approval",
                "control_command",
                "tool_name",
                "url",
                "script_name",
                "folder_path",
                "code_job_type",
                "repo_name",
                "goal",
                "branch_name",
                "send_updates",
                "runner",
                "subtasks"
            ]
        },
    )
    return PlannerDecision(**data)