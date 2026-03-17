from shared.config import DEFAULT_REPO_NAME, DEFAULT_CODE_RUNNER
from shared.tool_contracts import PlannerDecision

ALLOWED_SCRIPTS = {"daily_report", "cleanup_downloads", "stock_report"}
ALLOWED_FOLDERS = {"downloads", "desktop"}
ALLOWED_CONTROL_COMMANDS = {
    "pc_status",
    "pause_agent",
    "resume_agent",
    "queue_status",
    "stop_current_task",
    "latest_status",
    "wake_pc",
}
ALLOWED_CODE_RUNNERS = {"openai_local"}

def validate_command(cmd: PlannerDecision) -> PlannerDecision:
    if cmd.decision_type == "control":
        if not cmd.control_command or cmd.control_command not in ALLOWED_CONTROL_COMMANDS:
            raise ValueError(f"Control command not allowed: {cmd.control_command}")
        return cmd

    if cmd.decision_type == "task":
        if not cmd.tool_name:
            raise ValueError("Task decision missing tool_name")

        if cmd.tool_name == "run_named_script":
            if not cmd.script_name or cmd.script_name not in ALLOWED_SCRIPTS:
                raise ValueError(f"Script not allowed: {cmd.script_name}")

        if cmd.tool_name == "list_files_in_folder":
            if not cmd.folder_path or cmd.folder_path not in ALLOWED_FOLDERS:
                raise ValueError(f"Folder not allowed: {cmd.folder_path}")

        if cmd.tool_name == "open_url":
            if not cmd.url or not (cmd.url.startswith("http://") or cmd.url.startswith("https://")):
                raise ValueError("Invalid or missing URL")

        return cmd

    if cmd.decision_type == "code_job":
        if not cmd.code_job_type:
            raise ValueError("Code job missing code_job_type")
        if not cmd.goal:
            raise ValueError("Code job missing goal")

        if not cmd.repo_name:
            cmd.repo_name = DEFAULT_REPO_NAME

        if not cmd.runner:
            cmd.runner = DEFAULT_CODE_RUNNER

        if cmd.runner not in ALLOWED_CODE_RUNNERS:
            raise ValueError(f"Code runner not allowed: {cmd.runner}")

        if not cmd.branch_name:
            slug = cmd.goal.lower().replace("/", " ").replace("_", " ").replace("-", " ")
            slug = "-".join(slug.split()[:8]).strip("-")
            if not slug:
                slug = "update"
            cmd.branch_name = f"agent/{cmd.code_job_type}/{slug}"

        return cmd

    raise ValueError(f"Invalid decision type: {cmd.decision_type}")