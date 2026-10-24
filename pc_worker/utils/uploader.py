from pathlib import Path

from shared.artifact_links import signed_artifact_path
from shared.config import PUBLIC_BASE_URL

def get_public_artifact_url(file_path: str) -> str | None:
    path = Path(file_path)
    if not path.exists():
        return None

    signed_path = signed_artifact_path(path.name)
    if not PUBLIC_BASE_URL or not signed_path:
        return None

    return f"{PUBLIC_BASE_URL.rstrip('/')}{signed_path}"