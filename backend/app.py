from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from shared.artifact_links import is_valid_signature

from backend.routes.whatsapp import router as whatsapp_router
from backend.routes.tasks import router as tasks_router
from backend.routes.status import router as status_router
from backend.routes.app import router as app_router

app = FastAPI(title="WhatsApp PC Agent Backend")

@app.get("/health")
def health():
    return {"ok": True}

ROOT_DIR = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = ROOT_DIR / "pc_worker" / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

# Artifacts need a signed link (see shared/artifact_links.py); Twilio fetches these without auth headers.
@app.get("/artifacts/{name}", include_in_schema=False)
def get_artifact(name: str, sig: str = ""):
    if not is_valid_signature(name, sig):
        raise HTTPException(status_code=403, detail="Invalid or missing artifact signature")

    path = (OUTPUTS_DIR / name).resolve()
    if path.parent != OUTPUTS_DIR.resolve() or not path.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(path)

# Installable private app (PWA) for phone and laptop
APP_STATIC_DIR = Path(__file__).resolve().parent / "static" / "app"

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/app/")

app.mount("/app", StaticFiles(directory=str(APP_STATIC_DIR), html=True), name="app")

app.include_router(whatsapp_router)
app.include_router(tasks_router)
app.include_router(status_router)
app.include_router(app_router)