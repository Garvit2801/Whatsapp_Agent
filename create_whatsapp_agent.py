from pathlib import Path

# Base folder on Desktop
base = Path.home() / "Desktop" / "whatsapp-agent"

# Folders to create
folders = [
    "backend/routes",
    "backend/services",
    "backend/tools",
    "backend/db",
    "backend/workers",
    "pc_worker/executors",
    "pc_worker/utils",
    "shared",
    "infra",
]

# Files to create
files = [
    "backend/app.py",
    "backend/routes/whatsapp.py",
    "backend/routes/tasks.py",
    "backend/services/planner.py",
    "backend/services/validator.py",
    "backend/services/dispatcher.py",
    "backend/services/notifier.py",
    "backend/tools/schemas.py",
    "backend/db/models.py",
    "backend/db/session.py",
    "backend/workers/queue.py",
    "pc_worker/worker.py",
    "pc_worker/executors/screenshot.py",
    "pc_worker/executors/scripts.py",
    "pc_worker/executors/browser.py",
    "pc_worker/executors/files.py",
    "pc_worker/utils/uploader.py",
    "pc_worker/utils/logger.py",
    "pc_worker/utils/heartbeat.py",
    "shared/tool_contracts.py",
    "shared/config.py",
    "infra/docker-compose.yml",
    "infra/.env.example",
]

# Create folders
for folder in folders:
    (base / folder).mkdir(parents=True, exist_ok=True)

# Create files
for file in files:
    file_path = base / file
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.touch(exist_ok=True)

print(f"Folder structure created successfully at: {base}")