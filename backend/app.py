from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.routes.whatsapp import router as whatsapp_router
from backend.routes.tasks import router as tasks_router
from backend.routes.status import router as status_router

app = FastAPI(title="WhatsApp PC Agent Backend")

@app.get("/health")
def health():
    return {"ok": True}

ROOT_DIR = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = ROOT_DIR / "pc_worker" / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/artifacts", StaticFiles(directory=str(OUTPUTS_DIR)), name="artifacts")

app.include_router(whatsapp_router)
app.include_router(tasks_router)
app.include_router(status_router)