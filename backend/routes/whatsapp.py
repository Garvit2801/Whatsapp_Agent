import traceback
import uuid
from datetime import datetime

from fastapi import APIRouter, Form, Request
from twilio.request_validator import RequestValidator

from backend.services.planner import plan_command
from backend.services.validator import validate_command
from backend.services.dispatcher import (
    enqueue_task,
    set_task_waiting_approval,
    approve_task,
    reject_task,
    get_last_task_for_number,
    get_queue_summary,
    get_current_running_task,
    cancel_task,
    get_waiting_approval_tasks_for_number,
    get_waiting_approval_task_by_serial,
)
from backend.services.notifier import (
    send_task_received,
    send_task_waiting_approval,
    send_task_approved,
    send_task_rejected,
    send_no_pending_approval,
    send_status_summary,
    send_worker_status,
    send_agent_paused,
    send_agent_resumed,
    send_queue_summary,
    send_task_cancelled,
    send_unauthorized_sender,
    send_wake_attempted,
    send_code_job_received,
    send_waiting_approval_queue,
)
from backend.routes.status import get_worker_status_payload
from backend.services.control import set_paused, request_stop
from backend.services.wol import send_magic_packet
from shared.config import TWILIO_AUTH_TOKEN, ALLOWED_WHATSAPP_NUMBERS

router = APIRouter(prefix="/webhook", tags=["whatsapp"])

def _extract_command(user_text: str):
    parts = user_text.strip().split(maxsplit=1)
    action = parts[0].upper() if parts else ""
    rest = parts[1].strip() if len(parts) > 1 else None
    return action, rest

def _parse_yes_no_target(rest: str | None) -> int | None:
    if not rest:
        return None
    try:
        return int(rest.strip())
    except ValueError:
        return None

async def _is_valid_twilio_request(request: Request) -> bool:
    validator = RequestValidator(TWILIO_AUTH_TOKEN)
    form = await request.form()
    signature = request.headers.get("X-Twilio-Signature", "")
    return validator.validate(
        str(request.url),
        dict(form),
        signature,
    )

@router.post("/whatsapp")
async def whatsapp_webhook(
    request: Request,
    Body: str = Form(default=""),
    From: str = Form(default=""),
    To: str = Form(default=""),
    NumMedia: str = Form(default="0"),
):
    try:
        if not await _is_valid_twilio_request(request):
            return {"status": "forbidden", "message": "Invalid Twilio signature"}

        if ALLOWED_WHATSAPP_NUMBERS and From not in ALLOWED_WHATSAPP_NUMBERS:
            send_unauthorized_sender(From)
            return {"status": "forbidden", "message": "Unauthorized sender"}

        user_text = Body.strip()
        if not user_text:
            return {"status": "ignored", "reason": "empty body"}

        action, rest = _extract_command(user_text)

        if action in {"APPROVE", "REJECT", "YES", "NO", "APPROVALS"}:
            waiting_tasks = get_waiting_approval_tasks_for_number(From)

            if action == "APPROVALS":
                send_waiting_approval_queue(From, waiting_tasks)
                return {"status": "approval_queue_sent", "count": len(waiting_tasks)}

            if not waiting_tasks:
                send_no_pending_approval(From)
                return {"status": "no_pending_approval"}

            target_task = None

            if action in {"YES", "NO"}:
                serial_number = _parse_yes_no_target(rest)
                if serial_number is None:
                    target_task = waiting_tasks[0]
                else:
                    target_task = get_waiting_approval_task_by_serial(From, serial_number)

            elif action in {"APPROVE", "REJECT"}:
                if rest:
                    serial_number = _parse_yes_no_target(rest)
                    if serial_number is not None:
                        target_task = get_waiting_approval_task_by_serial(From, serial_number)
                    else:
                        # fallback to task id support
                        for t in waiting_tasks:
                            if t["id"] == rest:
                                target_task = t
                                break
                else:
                    target_task = waiting_tasks[0]

            if not target_task:
                send_waiting_approval_queue(From, waiting_tasks)
                return {"status": "approval_target_not_found"}

            task_id = target_task["id"]

            if action in {"APPROVE", "YES"}:
                task = approve_task(task_id)
                if not task:
                    send_no_pending_approval(From)
                    return {"status": "task_not_found"}
                send_task_approved(From, task_id)
                return {"status": "approved", "task_id": task_id}

            if action in {"REJECT", "NO"}:
                task = reject_task(task_id)
                if not task:
                    send_no_pending_approval(From)
                    return {"status": "task_not_found"}
                send_task_rejected(From, task_id)
                return {"status": "rejected", "task_id": task_id}

        planned = validate_command(plan_command(user_text))
        print("Planner decision:", planned.model_dump())

        if planned.decision_type == "control":
            command = planned.control_command

            if command == "pc_status":
                status = get_worker_status_payload()
                send_worker_status(From, status)
                return {"status": "worker_status_sent"}

            if command == "latest_status":
                latest_task = get_last_task_for_number(From)
                if not latest_task:
                    send_no_pending_approval(From)
                    return {"status": "no_task_found"}
                send_status_summary(From, latest_task)
                return {"status": "status_sent", "task_id": latest_task["id"]}

            if command == "pause_agent":
                set_paused(True)
                send_agent_paused(From)
                return {"status": "paused"}

            if command == "resume_agent":
                set_paused(False)
                send_agent_resumed(From)
                return {"status": "resumed"}

            if command == "queue_status":
                queued = get_queue_summary()
                send_queue_summary(From, queued)
                return {"status": "queue_sent", "count": len(queued)}

            if command == "stop_current_task":
                current_task = get_current_running_task()

                if current_task:
                    request_stop(current_task["id"])
                    cancel_task(current_task["id"], reason="Stopped by user")
                    send_task_cancelled(From, current_task["id"])
                    return {"status": "stopped", "task_id": current_task["id"]}

                queued = get_queue_summary(limit=50)
                pending_only = [t for t in queued if t["status"] in {"pending", "waiting_approval"}]
                if pending_only:
                    target = pending_only[0]
                    cancel_task(target["id"], reason="Stopped by user")
                    send_task_cancelled(From, target["id"])
                    return {"status": "stopped", "task_id": target["id"]}

                send_wake_attempted(From, "No running or queued task found to stop.")
                return {"status": "no_task_to_stop"}

            if command == "wake_pc":
                result = send_magic_packet()
                send_wake_attempted(From, result["message"])
                return {"status": "wake_sent"}

            return {"status": "ignored", "reason": "unsupported control command"}

        if planned.decision_type == "code_job":
            task = {
                "id": str(uuid.uuid4()),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "from_number": From,
                "to_number": To,
                "raw_command": user_text,
                "status": "pending",
                "tool_name": "code_job",
                "task_kind": "code_job",
                "reasoning": planned.reasoning,
                "requires_approval": planned.requires_approval,
                "approval_status": "pending" if planned.requires_approval else "not_required",
                "code_job": {
                    "code_job_type": planned.code_job_type,
                    "repo_name": planned.repo_name,
                    "goal": planned.goal,
                    "branch_name": planned.branch_name,
                    "send_updates": bool(planned.send_updates),
                    "runner": planned.runner,
                    "subtasks": planned.subtasks,
                },
                "args": {},
            }

            enqueue_task(task)

            if planned.requires_approval:
                set_task_waiting_approval(task["id"])
                waiting = get_waiting_approval_tasks_for_number(From)
                serial_number = 1
                for idx, item in enumerate(waiting, start=1):
                    if item["id"] == task["id"]:
                        serial_number = idx
                        break

                task["status"] = "waiting_approval"
                send_task_waiting_approval(From, task, serial_number, len(waiting))
                return {
                    "status": "waiting_approval",
                    "task_id": task["id"],
                    "tool_name": "code_job",
                    "requires_approval": True,
                }

            send_code_job_received(From, task)
            return {
                "status": "queued",
                "task_id": task["id"],
                "tool_name": "code_job",
                "requires_approval": False,
            }

        task = {
            "id": str(uuid.uuid4()),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "from_number": From,
            "to_number": To,
            "raw_command": user_text,
            "status": "pending",
            "tool_name": planned.tool_name,
            "task_kind": "task",
            "reasoning": planned.reasoning,
            "requires_approval": planned.requires_approval,
            "approval_status": "pending" if planned.requires_approval else "not_required",
            "args": {
                "url": planned.url,
                "script_name": planned.script_name,
                "folder_path": planned.folder_path,
            },
        }

        enqueue_task(task)

        if planned.requires_approval:
            set_task_waiting_approval(task["id"])
            waiting = get_waiting_approval_tasks_for_number(From)
            serial_number = 1
            for idx, item in enumerate(waiting, start=1):
                if item["id"] == task["id"]:
                    serial_number = idx
                    break

            task["status"] = "waiting_approval"
            send_task_waiting_approval(From, task, serial_number, len(waiting))
            return {
                "status": "waiting_approval",
                "task_id": task["id"],
                "tool_name": planned.tool_name,
                "requires_approval": True,
            }

        send_task_received(From, task)

        return {
            "status": "queued",
            "task_id": task["id"],
            "tool_name": planned.tool_name,
            "requires_approval": False,
        }

    except Exception as e:
        print("ERROR in /webhook/whatsapp:", str(e))
        traceback.print_exc()
        return {
            "status": "error",
            "message": str(e),
        }