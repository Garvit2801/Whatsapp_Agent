from pathlib import Path

from twilio.rest import Client

from backend.services.app_messages import is_app_recipient, add_message
from shared.artifact_links import signed_artifact_path
from shared.config import (
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_WHATSAPP_FROM,
)

# Twilio rejects WhatsApp bodies over 1600 characters.
MAX_BODY_CHARS = 1500

def _get_client() -> Client:
    return Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def _append_output(body: str, label: str, output: str | None) -> str:
    output = (output or "").strip()
    if not output:
        return body

    header = f"\n\n{label}:\n"
    room = MAX_BODY_CHARS - len(body) - len(header)
    if room <= 0:
        return body
    if len(output) > room:
        # Keep the end of the output, where results and errors usually are.
        output = "..." + output[-(room - 3):]
    return body + header + output

def send_whatsapp_text(to_number: str, body: str):
    if is_app_recipient(to_number):
        return add_message(to_number, "agent", body)

    client = _get_client()
    return client.messages.create(
        from_=TWILIO_WHATSAPP_FROM,
        to=to_number,
        body=body,
    )

def send_whatsapp_media(to_number: str, body: str, media_url: str):
    if is_app_recipient(to_number):
        return add_message(to_number, "agent", body, media_url=media_url)

    client = _get_client()
    return client.messages.create(
        from_=TWILIO_WHATSAPP_FROM,
        to=to_number,
        body=body,
        media_url=[media_url],
    )

def send_task_received(to_number: str, task: dict):
    body = (
        f"Task received.\n"
        f"ID: {task['id']}\n"
        f"Tool: {task['tool_name']}\n"
        f"Status: {task['status']}"
    )
    return send_whatsapp_text(to_number, body)

def send_task_waiting_approval(to_number: str, task: dict, serial_number: int, total_pending: int):
    label = f"approval #{serial_number}"
    body = (
        f"Approval needed for {label}.\n"
        f"Command: {task['raw_command']}\n"
        f"Planned action: {task['tool_name']}\n"
    )

    if total_pending <= 1:
        body += "\nReply YES or NO."
    else:
        body += (
            f"\nYou currently have {total_pending} approvals pending.\n"
            f"Reply YES {serial_number} or NO {serial_number}.\n"
            f"Example: YES 2"
        )

    return send_whatsapp_text(to_number, body)

def send_waiting_approval_queue(to_number: str, tasks: list[dict]):
    if not tasks:
        return send_whatsapp_text(to_number, "No pending approvals.")

    lines = ["Pending approvals:"]
    for idx, task in enumerate(tasks, start=1):
        lines.append(f"{idx}) {task['tool_name']} - {task['raw_command']}")
    lines.append("")
    lines.append("Reply YES <number> or NO <number>.")
    return send_whatsapp_text(to_number, "\n".join(lines))

def send_task_running(to_number: str, task: dict):
    body = (
        f"Task running.\n"
        f"ID: {task['id']}\n"
        f"Tool: {task['tool_name']}"
    )
    return send_whatsapp_text(to_number, body)

def send_task_completed(to_number: str, task: dict, result: dict):
    body = (
        f"Task completed.\n"
        f"ID: {task['id']}\n"
        f"Tool: {task['tool_name']}\n"
        f"Message: {result.get('message', 'Done')}"
    )
    body = _append_output(body, "Output", result.get("stdout"))

    artifact_url = result.get("artifact_url")
    artifact_path = result.get("artifact_path")
    validation_pdf = result.get("validation_report_pdf")

    if validation_pdf:
        body += f"\nValidation report PDF: {validation_pdf}"

    if artifact_url:
        return send_whatsapp_media(to_number, body, artifact_url)

    # The app is served by this backend, so artifacts work without a public URL.
    signed_path = artifact_path and signed_artifact_path(Path(artifact_path).name)
    if signed_path and is_app_recipient(to_number) and Path(artifact_path).is_file():
        return send_whatsapp_media(to_number, body, signed_path)

    if artifact_path:
        body += f"\nArtifact: {artifact_path}"

    return send_whatsapp_text(to_number, body)

def send_task_failed(to_number: str, task: dict, error_message: str):
    body = (
        f"Task failed.\n"
        f"ID: {task['id']}\n"
        f"Tool: {task['tool_name']}\n"
        f"Error: {error_message}"
    )
    result = task.get("result") or {}
    validation_pdf = result.get("validation_report_pdf")
    if validation_pdf:
        body += f"\nValidation report PDF: {validation_pdf}"
    body = _append_output(body, "Output", result.get("stdout"))
    body = _append_output(body, "Errors", result.get("stderr"))
    return send_whatsapp_text(to_number, body)

def send_task_approved(to_number: str, task_id: str):
    return send_whatsapp_text(
        to_number,
        f"Task {task_id} approved and moved to pending queue."
    )

def send_task_rejected(to_number: str, task_id: str):
    return send_whatsapp_text(
        to_number,
        f"Task {task_id} rejected and cancelled."
    )

def send_no_pending_approval(to_number: str):
    return send_whatsapp_text(
        to_number,
        "No pending approval task found for your number."
    )

def send_status_summary(to_number: str, task: dict):
    result = task.get("result") or {}
    body = (
        f"Latest task status\n"
        f"ID: {task['id']}\n"
        f"Status: {task['status']}\n"
        f"Tool: {task['tool_name']}\n"
        f"Command: {task['raw_command']}"
    )

    if result.get("message"):
        body += f"\nResult: {result['message']}"

    return send_whatsapp_text(to_number, body)

def send_worker_status(to_number: str, status: dict):
    body = (
        f"PC Worker Status\n"
        f"Online: {status.get('online', False)}\n"
        f"Last heartbeat: {status.get('last_heartbeat', 'N/A')}\n"
        f"Hostname: {status.get('hostname', 'N/A')}\n"
        f"Current task: {status.get('current_task_id', 'None')}\n"
        f"State: {status.get('state', 'idle')}\n"
        f"Agent paused: {status.get('agent_paused', False)}"
    )
    return send_whatsapp_text(to_number, body)

def send_agent_paused(to_number: str):
    return send_whatsapp_text(to_number, "Agent paused. New tasks will remain queued.")

def send_agent_resumed(to_number: str):
    return send_whatsapp_text(to_number, "Agent resumed. Queued tasks can run now.")

def send_queue_summary(to_number: str, tasks: list[dict]):
    if not tasks:
        return send_whatsapp_text(to_number, "Queue is empty.")

    lines = ["Queue summary:"]
    for t in tasks[:10]:
        lines.append(f"{t['id']} | {t['status']} | {t['tool_name']}")

    return send_whatsapp_text(to_number, "\n".join(lines))

def send_task_cancelled(to_number: str, task_id: str):
    return send_whatsapp_text(to_number, f"Task {task_id} cancelled.")

def send_unauthorized_sender(to_number: str):
    return send_whatsapp_text(to_number, "Unauthorized sender.")

def send_wake_attempted(to_number: str, message: str):
    return send_whatsapp_text(to_number, message)

def send_code_job_received(to_number: str, task: dict):
    job = task.get("code_job", {})
    body = (
        f"Code job received.\n"
        f"ID: {task['id']}\n"
        f"Repo: {job.get('repo_name', 'N/A')}\n"
        f"Type: {job.get('code_job_type', 'N/A')}\n"
        f"Branch: {job.get('branch_name', 'N/A')}\n"
        f"Goal: {job.get('goal', 'N/A')}"
    )
    return send_whatsapp_text(to_number, body)

def send_code_job_running(to_number: str, task: dict):
    job = task.get("code_job", {})
    body = (
        f"Code job running.\n"
        f"ID: {task['id']}\n"
        f"Repo: {job.get('repo_name', 'N/A')}\n"
        f"Branch: {job.get('branch_name', 'N/A')}\n"
        f"Goal: {job.get('goal', 'N/A')}"
    )
    return send_whatsapp_text(to_number, body)

def send_code_job_completed(to_number: str, task: dict, result: dict):
    summary = result.get("summary", result.get("message", "Done"))
    body = (
        f"Code job completed.\n"
        f"ID: {task['id']}\n"
        f"Repo: {task.get('code_job', {}).get('repo_name', 'N/A')}\n"
        f"Branch: {task.get('code_job', {}).get('branch_name', 'N/A')}\n"
        f"{summary}"
    )

    validation_pdf = result.get("validation_report_pdf")
    if validation_pdf:
        body += f"\nValidation report PDF: {validation_pdf}"

    artifact_path = result.get("artifact_path")
    if artifact_path:
        body += f"\nRun artifacts: {artifact_path}"
    return send_whatsapp_text(to_number, body)

def send_code_job_failed(to_number: str, task: dict, error_message: str):
    result = task.get("result") or {}
    body = (
        f"Code job failed.\n"
        f"ID: {task['id']}\n"
        f"Repo: {task.get('code_job', {}).get('repo_name', 'N/A')}\n"
        f"Branch: {task.get('code_job', {}).get('branch_name', 'N/A')}\n"
        f"Error: {error_message}"
    )
    validation_pdf = result.get("validation_report_pdf")
    if validation_pdf:
        body += f"\nValidation report PDF: {validation_pdf}"
    return send_whatsapp_text(to_number, body)