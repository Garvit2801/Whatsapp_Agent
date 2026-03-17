import sys
import time
import traceback
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from backend.services.dispatcher import (
    get_pending_tasks,
    set_task_running,
    mark_task_done,
    mark_task_failed,
    get_task_by_id,
)
from backend.services.notifier import (
    send_task_running,
    send_task_completed,
    send_task_failed,
    send_code_job_running,
    send_code_job_completed,
    send_code_job_failed,
)
from backend.services.control import get_control_state, clear_stop_request
from backend.services.update_summarizer import summarize_code_job_result
from pc_worker.executors.screenshot import take_screenshot
from pc_worker.executors.browser import open_url
from pc_worker.executors.files import list_files
from pc_worker.executors.scripts import run_named_script
from pc_worker.executors.openai_coder import run_openai_code_job
from pc_worker.utils.logger import log
from pc_worker.utils.heartbeat import write_heartbeat, mark_worker_offline
from pc_worker.utils.uploader import get_public_artifact_url

OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"

def execute_task(task: dict) -> dict:
    task_kind = task.get("task_kind", "task")
    tool_name = task["tool_name"]
    args = task.get("args", {}) or {}

    if task_kind == "code_job":
        return run_openai_code_job(task["id"], task["code_job"])

    if tool_name == "take_screenshot":
        return take_screenshot(task["id"], OUTPUT_DIR)

    if tool_name == "open_url":
        return open_url(args.get("url"))

    if tool_name == "list_files_in_folder":
        return list_files(args.get("folder_path"))

    if tool_name == "run_named_script":
        return run_named_script(args.get("script_name"))

    return {
        "success": False,
        "message": f"Unknown tool: {tool_name}",
    }

def main():
    log("PC worker started")

    try:
        while True:
            control = get_control_state()

            if control.get("paused"):
                write_heartbeat(current_task_id=None, state="paused")
                time.sleep(3)
                continue

            pending = get_pending_tasks()

            if pending:
                task = pending[0]
                task_id = task["id"]
                task_kind = task.get("task_kind", "task")

                try:
                    control = get_control_state()
                    if control.get("stop_requested") and (
                        control.get("stop_task_id") in {None, task_id}
                    ):
                        clear_stop_request()
                        write_heartbeat(current_task_id=None, state="idle")
                        time.sleep(1)
                        continue

                    write_heartbeat(current_task_id=task_id, state="running")
                    log(f"Processing task {task_id} -> {task['tool_name']}")
                    set_task_running(task_id)

                    task_after_update = get_task_by_id(task_id)
                    if task_after_update:
                        if task_kind == "code_job":
                            send_code_job_running(task_after_update["from_number"], task_after_update)
                        else:
                            send_task_running(task_after_update["from_number"], task_after_update)

                    control = get_control_state()
                    if control.get("stop_requested") and (
                        control.get("stop_task_id") in {None, task_id}
                    ):
                        clear_stop_request()
                        mark_task_failed(task_id, "Stopped by user")
                        stopped_task = get_task_by_id(task_id)
                        if stopped_task:
                            if task_kind == "code_job":
                                send_code_job_failed(stopped_task["from_number"], stopped_task, "Stopped by user")
                            else:
                                send_task_failed(stopped_task["from_number"], stopped_task, "Stopped by user")
                        write_heartbeat(current_task_id=None, state="idle")
                        time.sleep(1)
                        continue

                    result = execute_task(task)
                    result["finished_at"] = datetime.utcnow().isoformat()

                    artifact_path = result.get("artifact_path")
                    if artifact_path:
                        result["artifact_url"] = get_public_artifact_url(artifact_path)

                    if task_kind == "code_job":
                        result["summary"] = summarize_code_job_result(task, result)

                    if result.get("success"):
                        mark_task_done(task_id, result)
                        finished_task = get_task_by_id(task_id)
                        if finished_task:
                            if task_kind == "code_job":
                                send_code_job_completed(finished_task["from_number"], finished_task, result)
                            else:
                                send_task_completed(finished_task["from_number"], finished_task, result)
                    else:
                        error_message = result.get("message", "Task failed")
                        mark_task_failed(task_id, error_message, extra=result)
                        failed_task = get_task_by_id(task_id)
                        if failed_task:
                            if task_kind == "code_job":
                                # include current result so notifier can show validation PDF path
                                failed_task["result"] = result
                                send_code_job_failed(failed_task["from_number"], failed_task, error_message)
                            else:
                                failed_task["result"] = result
                                send_task_failed(failed_task["from_number"], failed_task, error_message)

                except Exception as e:
                    traceback.print_exc()
                    error_message = str(e)
                    mark_task_failed(task_id, error_message)
                    failed_task = get_task_by_id(task_id)
                    if failed_task:
                        if task_kind == "code_job":
                            send_code_job_failed(failed_task["from_number"], failed_task, error_message)
                        else:
                            send_task_failed(failed_task["from_number"], failed_task, error_message)

            write_heartbeat(current_task_id=None, state="idle")
            time.sleep(3)

    except KeyboardInterrupt:
        log("PC worker stopping")
        mark_worker_offline()
        raise
    except Exception:
        mark_worker_offline()
        raise

if __name__ == "__main__":
    main()