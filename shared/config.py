import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
TWILIO_WHATSAPP_TO = os.getenv("TWILIO_WHATSAPP_TO", "")

TASKS_FILE = str(BASE_DIR / os.getenv("TASKS_FILE", "tasks.json"))
RESULTS_FILE = str(BASE_DIR / os.getenv("RESULTS_FILE", "results.json"))

APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "")

ALLOWED_WHATSAPP_NUMBERS = {
    x.strip()
    for x in os.getenv("ALLOWED_WHATSAPP_NUMBERS", "").split(",")
    if x.strip()
}

# Private app channel (installable PWA, replaces Twilio for personal use)
APP_ACCESS_TOKEN = os.getenv("APP_ACCESS_TOKEN", "").strip()
APP_MESSAGES_FILE = str(BASE_DIR / os.getenv("APP_MESSAGES_FILE", "app_messages.jsonl"))

AGENT_CONTROL_FILE = str(BASE_DIR / os.getenv("AGENT_CONTROL_FILE", "agent_control.json"))

WOL_TARGET_MAC = os.getenv("WOL_TARGET_MAC", "").strip()
WOL_BROADCAST_IP = os.getenv("WOL_BROADCAST_IP", "255.255.255.255").strip()
WOL_PORT = int(os.getenv("WOL_PORT", "9"))

# Coding agent settings
CODING_WORKSPACE_ROOT = str(BASE_DIR / os.getenv("CODING_WORKSPACE_ROOT", "workspace"))
CODING_RUNS_ROOT = str(BASE_DIR / os.getenv("CODING_RUNS_ROOT", "coding_runs"))
DEFAULT_REPO_NAME = os.getenv("DEFAULT_REPO_NAME", "product")
DEFAULT_CODE_RUNNER = os.getenv("DEFAULT_CODE_RUNNER", "openai_local")

CODE_AGENT_MODEL = os.getenv("CODE_AGENT_MODEL", "gpt-5.4")
CODE_AGENT_MAX_FILES = int(os.getenv("CODE_AGENT_MAX_FILES", "8"))
CODE_AGENT_MAX_FILE_BYTES = int(os.getenv("CODE_AGENT_MAX_FILE_BYTES", "40000"))