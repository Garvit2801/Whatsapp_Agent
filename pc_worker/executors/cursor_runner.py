import json
import shlex
import subprocess
from pathlib import Path

from shared.config import CODING_WORKSPACE_ROOT, CODING_RUNS_ROOT, CURSOR_AGENT_COMMAND

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
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return lines

def _build_prompt(code_job: dict) -> str:
    repo_name = code_job["repo_name"]
    goal = code_job["goal"]
    branch_name = code_job["branch_name"]
    subtasks = code_job.get("subtasks") or []

    parts = [
        f"Repo: {repo_name}",
        f"Branch: {branch_name}",
        f"Goal: {goal}",
        "",
        "Requirements:",
        "- Make changes directly in the repo.",
        "- Prefer minimal, safe changes.",
        "- Keep the repo buildable.",
        "- If tests or lint are available, run the most relevant ones.",
        "- Summarize what changed at the end.",
    ]

    if subtasks:
        parts.append("")
        parts.append("Suggested subtasks:")
        for item in subtasks:
            parts.append(f"- {item}")

    return "\n".join(parts)

def run_cursor_job(task_id: str, code_job: dict) -> dict:
    if not CURSOR_AGENT_COMMAND:
        return {
            "success": False,
            "message": "CURSOR_AGENT_COMMAND is not configured.",
        }

    repo_name = code_job["repo_name"]
    goal = code_job["goal"]
    branch_name = code_job["branch_name"]

    repo_path = _repo_path(repo_name)
    if not repo_path.exists():
        return {
            "success": False,
            "message": f"Repo path not found: {repo_path}",
        }

    run_dir = _run_dir(task_id)
    prompt_file = run_dir / "cursor_prompt.md"
    stdout_file = run_dir / "stdout.txt"
    stderr_file = run_dir / "stderr.txt"
    metadata_file = run_dir / "metadata.json"

    full_prompt = _build_prompt(code_job)
    _write_text(prompt_file, full_prompt)

    _safe_git_branch(repo_path, branch_name)

    command_str = CURSOR_AGENT_COMMAND.format(
        repo_path=str(repo_path),
        prompt_file=str(prompt_file),
        branch_name=branch_name,
        goal=full_prompt,
    )
    command = shlex.split(command_str)

    result = subprocess.run(
        command,
        cwd=str(repo_path),
        capture_output=True,
        text=True,
        timeout=3600,
    )

    _write_text(stdout_file, result.stdout or "")
    _write_text(stderr_file, result.stderr or "")

    changed_files = _git_changed_files(repo_path)

    metadata = {
        "repo_name": repo_name,
        "branch_name": branch_name,
        "goal": goal,
        "full_prompt": full_prompt,
        "command": command,
        "returncode": result.returncode,
        "changed_files": changed_files,
    }
    metadata_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    if result.returncode != 0:
        return {
            "success": False,
            "message": f"Cursor runner failed with exit code {result.returncode}",
            "artifact_path": str(run_dir),
            "stdout": (result.stdout or "")[-4000:],
            "stderr": (result.stderr or "")[-4000:],
            "changed_files": changed_files,
        }

    return {
        "success": True,
        "message": "Cursor job completed successfully.",
        "artifact_path": str(run_dir),
        "stdout": (result.stdout or "")[-4000:],
        "stderr": (result.stderr or "")[-2000:],
        "changed_files": changed_files,
    }