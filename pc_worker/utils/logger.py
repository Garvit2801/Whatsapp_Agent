from datetime import datetime

def log(message: str):
    print(f"[{datetime.utcnow().isoformat()}] {message}")