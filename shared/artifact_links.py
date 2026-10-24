import hashlib
import hmac
from typing import Optional

from shared.config import APP_ACCESS_TOKEN

# Artifact links carry an HMAC of the file name, keyed with APP_ACCESS_TOKEN.
# Twilio and <img> tags can't send an Authorization header, but they can follow a signed URL.
# Rotating APP_ACCESS_TOKEN invalidates every link issued before.

def _signature(name: str) -> str:
    key = hashlib.sha256(b"artifacts:" + APP_ACCESS_TOKEN.encode()).digest()
    return hmac.new(key, name.encode(), hashlib.sha256).hexdigest()

def signed_artifact_path(name: str) -> Optional[str]:
    if not APP_ACCESS_TOKEN:
        return None
    return f"/artifacts/{name}?sig={_signature(name)}"

def is_valid_signature(name: str, sig: str) -> bool:
    if not APP_ACCESS_TOKEN or not sig:
        return False
    return hmac.compare_digest(sig, _signature(name))
