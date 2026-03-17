from pathlib import Path

def summarize_code_job_result(task: dict, execution: dict) -> str:
    job = task.get("code_job", {})
    repo_name = job.get("repo_name", "repo")
    branch_name = job.get("branch_name", "agent/unknown")
    changed_files = execution.get("changed_files", [])
    stdout_tail = (execution.get("stdout") or "").strip()
    stderr_tail = (execution.get("stderr") or "").strip()

    lines = [
        f"Repo: {repo_name}",
        f"Branch: {branch_name}",
    ]

    if changed_files:
        lines.append("Changed files:")
        for path in changed_files[:8]:
            lines.append(f"- {path}")

    if stdout_tail:
        lines.append("Runner output:")
        lines.append(stdout_tail[:700])

    if stderr_tail:
        lines.append("Errors:")
        lines.append(stderr_tail[:400])

    if not changed_files and not stdout_tail and not stderr_tail:
        lines.append("No detailed output was captured.")

    return "\n".join(lines)