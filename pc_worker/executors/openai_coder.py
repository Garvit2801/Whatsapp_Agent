import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any

from shared.config import (
    CODE_AGENT_MODEL,
    CODING_WORKSPACE_ROOT,
    CODING_RUNS_ROOT,
    CODE_AGENT_MAX_FILES,
    CODE_AGENT_MAX_FILE_BYTES,
)
from shared.llm import structured_completion
from pc_worker.utils.pdf_reports import generate_validation_report_pdf

EXCLUDED_DIRS = {
    ".git",
    "node_modules",
    ".next",
    "dist",
    "build",
    ".venv",
    "venv",
    "__pycache__",
    ".cursor",
}

ALLOWED_TEST_PREFIXES = [
    "npm test",
    "npm run test",
    "npm run lint",
    "npm run build",
    "pnpm test",
    "pnpm run test",
    "pnpm run lint",
    "pnpm run build",
    "yarn test",
    "yarn lint",
    "yarn build",
    "pytest",
    "python -m pytest",
    "python3 -m pytest",
    "python -m py_compile",
    "python3 -m py_compile",
    "python -m compileall",
    "python3 -m compileall",
]

def _repo_path(repo_name: str) -> Path:
    return Path(CODING_WORKSPACE_ROOT) / repo_name

def _run_dir(task_id: str) -> Path:
    path = Path(CODING_RUNS_ROOT) / task_id
    path.mkdir(parents=True, exist_ok=True)
    return path

def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")

def _safe_git_branch(repo_path: Path, branch_name: str) -> None:
    if not (repo_path / ".git").exists():
        return
    subprocess.run(
        ["git", "-C", str(repo_path), "checkout", "-B", branch_name],
        capture_output=True,
        text=True,
        timeout=60,
    )

def _git_changed_files(repo_path: Path) -> list[str]:
    if not (repo_path / ".git").exists():
        return []
    result = subprocess.run(
        ["git", "-C", str(repo_path), "status", "--short"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]

def _render_repo_tree(repo_path: Path, limit: int = 300) -> str:
    lines: list[str] = []
    count = 0

    for root, dirs, files in os.walk(repo_path):
        rel_root = Path(root).relative_to(repo_path)
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".cache")]
        files = [f for f in files if f != ".DS_Store"]

        if rel_root != Path("."):
            indent = "  " * len(rel_root.parts)
            lines.append(f"{indent}{rel_root.name}/")

        for f in sorted(files):
            if count >= limit:
                lines.append("... tree truncated ...")
                return "\n".join(lines)
            indent = "  " * (0 if rel_root == Path(".") else len(rel_root.parts) + 1)
            lines.append(f"{indent}{f}")
            count += 1

    return "\n".join(lines)

def _safe_rel_path(repo_path: Path, rel_path: str) -> Path:
    target = (repo_path / rel_path).resolve()
    repo_resolved = repo_path.resolve()
    if not str(target).startswith(str(repo_resolved)):
        raise ValueError(f"Path escapes repo: {rel_path}")
    return target

def _read_text_file(repo_path: Path, rel_path: str) -> str:
    target = _safe_rel_path(repo_path, rel_path)
    if not target.exists() or not target.is_file():
        raise ValueError(f"File not found: {rel_path}")

    size = target.stat().st_size
    if size > CODE_AGENT_MAX_FILE_BYTES:
        raise ValueError(f"File too large to read: {rel_path}")

    return target.read_text(encoding="utf-8", errors="replace")

def _write_text_file(repo_path: Path, rel_path: str, content: str) -> None:
    target = _safe_rel_path(repo_path, rel_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")

def _delete_file(repo_path: Path, rel_path: str) -> None:
    target = _safe_rel_path(repo_path, rel_path)
    if target.exists() and target.is_file():
        target.unlink()

def _call_structured(name: str, schema: dict[str, Any], instructions: str, input_text: str) -> dict[str, Any]:
    return structured_completion(CODE_AGENT_MODEL, name, schema, instructions, input_text)

def _is_allowed_repo_command(command: str) -> bool:
    cmd = command.strip()

    if any(cmd.startswith(prefix) for prefix in ALLOWED_TEST_PREFIXES):
        return True

    if cmd.startswith("python ") or cmd.startswith("python3 "):
        blocked = ["http://", "https://", "rm ", "sudo ", "pip install", "curl ", "wget "]
        if any(x in cmd for x in blocked):
            return False
        return True

    return False

def _run_repo_command(repo_path: Path, command: str) -> dict[str, Any]:
    if not _is_allowed_repo_command(command):
        return {
            "success": False,
            "command": command,
            "message": "Command not in allowed test/build allowlist.",
        }

    result = subprocess.run(
        shlex.split(command),
        cwd=str(repo_path),
        capture_output=True,
        text=True,
        timeout=900,
    )
    return {
        "success": result.returncode == 0,
        "command": command,
        "returncode": result.returncode,
        "stdout": (result.stdout or "")[-4000:],
        "stderr": (result.stderr or "")[-4000:],
    }

def _analysis_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "summary": {"type": "string"},
            "files_to_read": {
                "type": "array",
                "items": {"type": "string"}
            },
            "test_commands": {
                "type": "array",
                "items": {"type": "string"}
            },
            "needs_clarification": {"type": "boolean"},
            "clarification_question": {"type": ["string", "null"]},
        },
        "required": [
            "summary",
            "files_to_read",
            "test_commands",
            "needs_clarification",
            "clarification_question",
        ],
    }

def _implementation_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "summary": {"type": "string"},
            "files_to_write": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
            },
            "files_to_delete": {
                "type": "array",
                "items": {"type": "string"},
            },
            "test_commands": {
                "type": "array",
                "items": {"type": "string"}
            },
            "notes": {
                "type": "array",
                "items": {"type": "string"}
            },
        },
        "required": ["summary", "files_to_write", "files_to_delete", "test_commands", "notes"],
    }

def run_openai_code_job(task_id: str, code_job: dict) -> dict:
    repo_name = code_job["repo_name"]
    goal = code_job["goal"]
    branch_name = code_job["branch_name"]
    job_type = code_job["code_job_type"]
    subtasks = code_job.get("subtasks") or []

    repo_path = _repo_path(repo_name)
    if not repo_path.exists():
        return {
            "success": False,
            "message": f"Repo path not found: {repo_path}",
        }

    run_dir = _run_dir(task_id)
    prompt_file = run_dir / "goal.txt"
    analysis_file = run_dir / "analysis.json"
    implementation_file = run_dir / "implementation.json"
    stdout_file = run_dir / "stdout.txt"
    stderr_file = run_dir / "stderr.txt"
    metadata_file = run_dir / "metadata.json"
    validation_pdf_path = run_dir / "validation_report.pdf"

    _write_text(prompt_file, goal)
    _safe_git_branch(repo_path, branch_name)

    repo_tree = _render_repo_tree(repo_path)
    initial_status = "\n".join(_git_changed_files(repo_path)) or "No local changes detected."

    analyze_instructions = """
You are an expert coding agent.
Given a repo tree and a coding goal, decide the minimum set of files that must be read before editing.
Prefer reading as few files as possible.
Only ask for clarification if the goal is too ambiguous to act safely.
Recommend only safe test/build commands from common repo commands.
"""

    analyze_input = "\n".join([
        f"Job type: {job_type}",
        f"Goal: {goal}",
        f"Suggested subtasks: {subtasks}",
        "",
        "Current repo tree:",
        repo_tree,
        "",
        "Current git status:",
        initial_status,
    ])

    analysis = _call_structured(
        name="code_job_analysis",
        schema=_analysis_schema(),
        instructions=analyze_instructions,
        input_text=analyze_input,
    )
    analysis_file.write_text(json.dumps(analysis, indent=2), encoding="utf-8")

    if analysis["needs_clarification"]:
        question = analysis["clarification_question"] or "The request needs clarification."
        return {
            "success": False,
            "message": question,
            "artifact_path": str(run_dir),
            "stdout": "",
            "stderr": "",
            "changed_files": [],
        }

    files_to_read = analysis["files_to_read"][:CODE_AGENT_MAX_FILES]
    file_context_blocks: list[str] = []
    loaded_files: list[str] = []

    for rel_path in files_to_read:
        try:
            content = _read_text_file(repo_path, rel_path)
            file_context_blocks.append(f"FILE: {rel_path}\n---\n{content}\n")
            loaded_files.append(rel_path)
        except Exception as e:
            file_context_blocks.append(f"FILE: {rel_path}\n---\n<UNREADABLE: {e}>\n")

    implementation_instructions = """
You are an expert coding agent editing a local repo.
Return full replacement contents for only the files that need to change.
If a file should be removed, include its relative path in files_to_delete.
Do not include markdown fences.
Do not invent files unless truly necessary.
Keep changes minimal and aligned with the goal.
If no file changes are needed, return empty arrays and explain why in summary.
Recommend only safe test/build commands.
"""

    implementation_input = "\n".join([
        f"Job type: {job_type}",
        f"Goal: {goal}",
        f"Branch: {branch_name}",
        "",
        "Repo tree:",
        repo_tree,
        "",
        "Loaded file contents:",
        "\n".join(file_context_blocks),
        "",
        "Suggested subtasks:",
        "\n".join(f"- {x}" for x in subtasks) if subtasks else "None",
        "",
        "Recommended test commands from analysis:",
        "\n".join(f"- {x}" for x in analysis["test_commands"]) if analysis["test_commands"] else "None",
    ])

    implementation = _call_structured(
        name="code_job_implementation",
        schema=_implementation_schema(),
        instructions=implementation_instructions,
        input_text=implementation_input,
    )
    implementation_file.write_text(json.dumps(implementation, indent=2), encoding="utf-8")

    written_files: list[str] = []
    deleted_files: list[str] = []

    for item in implementation["files_to_write"]:
        _write_text_file(repo_path, item["path"], item["content"])
        written_files.append(item["path"])

    for rel_path in implementation["files_to_delete"]:
        _delete_file(repo_path, rel_path)
        deleted_files.append(rel_path)

    command_results: list[dict[str, Any]] = []
    combined_stdout_parts: list[str] = []
    combined_stderr_parts: list[str] = []

    for command in implementation["test_commands"]:
        result = _run_repo_command(repo_path, command)
        command_results.append(result)
        if result.get("stdout"):
            combined_stdout_parts.append(f"$ {command}\n{result['stdout']}")
        if result.get("stderr"):
            combined_stderr_parts.append(f"$ {command}\n{result['stderr']}")
        if result.get("message") and not result.get("stdout") and not result.get("stderr"):
            combined_stderr_parts.append(f"$ {command}\n{result['message']}")

    changed_files = _git_changed_files(repo_path)

    validation_report_pdf = generate_validation_report_pdf(
        output_path=str(validation_pdf_path),
        repo_name=repo_name,
        branch_name=branch_name,
        goal=goal,
        written_files=written_files,
        deleted_files=deleted_files,
        changed_files=changed_files,
        command_results=command_results,
    )

    metadata = {
        "repo_name": repo_name,
        "branch_name": branch_name,
        "goal": goal,
        "job_type": job_type,
        "loaded_files": loaded_files,
        "written_files": written_files,
        "deleted_files": deleted_files,
        "analysis": analysis,
        "implementation": implementation,
        "command_results": command_results,
        "changed_files": changed_files,
        "validation_report_pdf": validation_report_pdf,
    }
    metadata_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    _write_text(stdout_file, "\n\n".join(combined_stdout_parts))
    _write_text(stderr_file, "\n\n".join(combined_stderr_parts))

    failed_commands = [x for x in command_results if not x.get("success")]

    if failed_commands:
        return {
            "success": False,
            "message": "Code changes were applied, but one or more validation commands failed.",
            "summary": implementation["summary"],
            "artifact_path": str(run_dir),
            "validation_report_pdf": validation_report_pdf,
            "stdout": "\n\n".join(combined_stdout_parts)[-4000:],
            "stderr": "\n\n".join(combined_stderr_parts)[-4000:],
            "changed_files": changed_files,
            "deleted_files": deleted_files,
        }

    return {
        "success": True,
        "message": "Code job completed successfully.",
        "summary": implementation["summary"],
        "artifact_path": str(run_dir),
        "validation_report_pdf": validation_report_pdf,
        "stdout": "\n\n".join(combined_stdout_parts)[-4000:],
        "stderr": "\n\n".join(combined_stderr_parts)[-2000:],
        "changed_files": changed_files,
        "deleted_files": deleted_files,
    }