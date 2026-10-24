import traceback

from fastapi import APIRouter, Form, Request
from twilio.request_validator import RequestValidator

from backend.services.command_handler import handle_command
from backend.services.notifier import send_unauthorized_sender
from shared.config import TWILIO_AUTH_TOKEN, ALLOWED_WHATSAPP_NUMBERS

router = APIRouter(prefix="/webhook", tags=["whatsapp"])

async def _is_valid_twilio_request(request: Request) -> bool:
    validator = RequestValidator(TWILIO_AUTH_TOKEN)
    form = await request.form()
    signature = request.headers.get("X-Twilio-Signature", "")
    return validator.validate(
        str(request.url),
        dict(form),
        signature,
    )

@router.post("/whatsapp")
async def whatsapp_webhook(
    request: Request,
    Body: str = Form(default=""),
    From: str = Form(default=""),
    To: str = Form(default=""),
    NumMedia: str = Form(default="0"),
):
    try:
        if not await _is_valid_twilio_request(request):
            return {"status": "forbidden", "message": "Invalid Twilio signature"}

        if ALLOWED_WHATSAPP_NUMBERS and From not in ALLOWED_WHATSAPP_NUMBERS:
            send_unauthorized_sender(From)
            return {"status": "forbidden", "message": "Unauthorized sender"}

        return handle_command(From, To, Body)

    except Exception as e:
        print("ERROR in /webhook/whatsapp:", str(e))
        traceback.print_exc()
        return {
            "status": "error",
            "message": str(e),
        }