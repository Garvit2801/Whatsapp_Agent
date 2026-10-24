import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from shared.config import APP_MESSAGES_FILE

APP_PREFIX = "app:"

# Append-only JSON Lines log. The backend and the PC worker both write to it,
# and single-line appends are safe without extra locking, unlike rewriting a JSON array.

def is_app_recipient(number: Optional[str]) -> bool:
    return bool(number) and number.startswith(APP_PREFIX)

def add_message(
    conversation: str,
    sender: str,
    text: str,
    media_url: Optional[str] = None,
) -> Dict[str, Any]:
    message = {
        "id": str(uuid.uuid4()),
        "conversation": conversation,
        "sender": sender,
        "text": text,
        "media_url": media_url,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(APP_MESSAGES_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(message) + "\n")
    return message

def get_messages(conversation: str, after: int = 0) -> Tuple[List[Dict[str, Any]], int]:
    """Return messages from line ``after`` onwards plus the cursor for the next poll."""
    if not os.path.exists(APP_MESSAGES_FILE):
        return [], 0

    messages = []
    next_seq = after
    with open(APP_MESSAGES_FILE, "r", encoding="utf-8") as f:
        for seq, line in enumerate(f):
            if seq < after:
                continue
            if not line.endswith("\n"):
                # A concurrent append is still in progress; pick it up next poll.
                break
            next_seq = seq + 1
            message = json.loads(line)
            if message.get("conversation") == conversation:
                messages.append(message)
    return messages, next_seq
