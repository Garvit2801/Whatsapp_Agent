import os
import shutil
import time
from datetime import datetime
from pathlib import Path

DOWNLOADS_DIR = Path.home() / "Downloads"
ARCHIVE_DIR = DOWNLOADS_DIR / "_old"
MAX_AGE_DAYS = int(os.getenv("CLEANUP_MAX_AGE_DAYS", "30"))

# Browsers write these while a download is still in progress.
IN_PROGRESS_SUFFIXES = {".crdownload", ".download", ".part", ".partial"}

def main():
    # Nothing is deleted: old files are moved into ~/Downloads/_old/<date>/ so they can be restored.
    cutoff = time.time() - MAX_AGE_DAYS * 86400
    target_dir = ARCHIVE_DIR / datetime.now().strftime("%Y-%m-%d")

    moved = []
    for item in DOWNLOADS_DIR.iterdir():
        if item == ARCHIVE_DIR or item.name.startswith("."):
            continue
        if item.suffix.lower() in IN_PROGRESS_SUFFIXES:
            continue
        if item.stat().st_mtime >= cutoff:
            continue

        target_dir.mkdir(parents=True, exist_ok=True)
        destination = target_dir / item.name
        if destination.exists():
            destination = target_dir / f"{item.stem}_{int(time.time())}{item.suffix}"
        shutil.move(str(item), str(destination))
        moved.append(item.name)

    print(f"Moved {len(moved)} item(s) older than {MAX_AGE_DAYS} days to {target_dir}")
    for name in moved[:20]:
        print(f"  - {name}")

if __name__ == "__main__":
    main()
