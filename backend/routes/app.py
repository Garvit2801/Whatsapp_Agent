import hmac
import traceback

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from backend.routes.status import get_worker_status_payload
from backend.services.app_messages import add_message, get_messages
from backend.services.command_handler import handle_command
from shared.config import APP_ACCESS_TOKEN

# Single private owner. Replies for this "number" are routed to the app by the notifier.
APP_CONVERSATION = "app:owner"

router = APIRouter(prefix="/api/app", tags=["app"])

class SendMessageRequest(BaseModel):
    text: str

def require_app_token(authorization: str = Header(default="")):
    if not APP_ACCESS_TOKEN:
        raise HTTPException(status_code=503, detail="APP_ACCESS_TOKEN is not configured on the server")

    token = authorization.removeprefix("Bearer ").strip()
    if not hmac.compare_digest(token, APP_ACCESS_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid access token")

@router.get("/messages", dependencies=[Depends(require_app_token)])
def list_messages(after: int = 0):
    messages, next_seq = get_messages(APP_CONVERSATION, after=after)
    return {"messages": messages, "next": next_seq}

@router.post("/messages", dependencies=[Depends(require_app_token)])
def send_message(payload: SendMessageRequest):
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message is empty")

    add_message(APP_CONVERSATION, "user", text)

    try:
        return handle_command(APP_CONVERSATION, "app", text)
    except Exception as e:
        print("ERROR in /api/app/messages:", str(e))
        traceback.print_exc()
        add_message(APP_CONVERSATION, "agent", f"Error: {e}")
        return {"status": "error", "message": str(e)}

@router.get("/status", dependencies=[Depends(require_app_token)])
def app_status():
    return get_worker_status_payload()
