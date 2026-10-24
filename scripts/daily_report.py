import json
import shutil
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from shared.config import TASKS_FILE

def _load_tasks() -> list[dict]:
    path = Path(TASKS_FILE)
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    # Task timestamps are written with datetime.utcnow(), so compare in naive UTC.
    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=24)
    recent = [
        t for t in _load_tasks()
        if t.get("created_at") and datetime.fromisoformat(t["created_at"]) >= since
    ]

    print(f"Daily report ({datetime.now():%Y-%m-%d %H:%M})")
    print(f"Tasks in last 24h: {len(recent)}")

    for status, count in Counter(t.get("status", "unknown") for t in recent).most_common():
        print(f"  {status}: {count}")

    failed = [t for t in recent if t.get("status") == "failed"]
    if failed:
        print("Failed tasks:")
        for t in failed[-5:]:
            print(f"  - {t.get('raw_command', '')[:60]} ({t['id'][:8]})")

    disk = shutil.disk_usage(Path.home())
    print(f"Disk free: {disk.free / 1e9:.1f} GB of {disk.total / 1e9:.1f} GB")

if __name__ == "__main__":
    main()
