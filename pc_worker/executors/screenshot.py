from pathlib import Path
import pyautogui

def take_screenshot(task_id: str, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = output_dir / f"{task_id}_screenshot.png"
    image = pyautogui.screenshot()
    image.save(filename)
    print(f"Screenshot saved at: {filename}")

    return {
        "success": True,
        "message": "Screenshot captured",
        "artifact_path": str(filename),
    }