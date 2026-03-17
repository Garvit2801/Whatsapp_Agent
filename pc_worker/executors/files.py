from pathlib import Path

ALLOWED_FOLDERS = {
    "downloads": str(Path.home() / "Downloads"),
    "desktop": str(Path.home() / "Desktop"),
}

def list_files(folder_key: str) -> dict:
    folder_path = ALLOWED_FOLDERS.get(folder_key)
    if not folder_path:
        return {"success": False, "message": f"Folder key not allowed: {folder_key}"}

    p = Path(folder_path)
    if not p.exists() or not p.is_dir():
        return {"success": False, "message": f"Folder not found: {folder_path}"}

    items = []
    for x in p.iterdir():
        items.append({
            "name": x.name,
            "is_dir": x.is_dir(),
            "size": x.stat().st_size if x.is_file() else None,
        })

    return {
        "success": True,
        "message": f"Listed {len(items)} items",
        "items": items[:50],
    }