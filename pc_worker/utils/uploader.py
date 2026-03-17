from pathlib import Path

from shared.config import PUBLIC_BASE_URL

def get_public_artifact_url(file_path: str) -> str | None:
    path = Path(file_path)
    if not path.exists():
        return None

    if not PUBLIC_BASE_URL:
        return None

    return f"{PUBLIC_BASE_URL.rstrip('/')}/artifacts/{path.name}"