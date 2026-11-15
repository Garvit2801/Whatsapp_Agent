import re

from shared.tool_contracts import PlannerDecision

# Common short commands are matched here so they don't need the LLM: instant
# replies, and the local model stays unloaded. Patterns must match the whole
# (normalized) message, so "fix the screenshot feature" still goes to the LLM.

_FILLER = re.compile(
    r"^(?:(?:hey|hi|ok|okay|please|pls|can you|could you|would you|will you|"
    r"i want you to|i want to|i'd like to|let me|kindly|just|now)\s+)+"
)
_TRAILING = re.compile(r"\s+(?:please|pls|now|for me|thanks|thank you)$")

def _normalize(text: str) -> str:
    text = text.lower().strip()
    # Keep dots inside words so domains like youtube.com survive.
    text = re.sub(r"[?!,]+|\.+(?=\s|$)", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = _FILLER.sub("", text)
    while True:
        stripped = _TRAILING.sub("", text)
        if stripped == text:
            return text
        text = stripped

def _control(command: str) -> PlannerDecision:
    return PlannerDecision(
        decision_type="control",
        reasoning="Matched a quick command.",
        control_command=command,
    )

def _task(tool_name: str, **fields) -> PlannerDecision:
    return PlannerDecision(
        decision_type="task",
        reasoning="Matched a quick command.",
        tool_name=tool_name,
        **fields,
    )

_MY = r"(?:my |the )?"
_PC = r"(?:pc|computer|laptop|mac|machine|worker|agent)"

_RULES = [
    (rf"(?:{_PC} )?status|is {_MY}{_PC} (?:online|on|up|running|awake)|"
     rf"(?:check|show|get) {_MY}{_PC} status|ping",
     lambda m: _control("pc_status")),
    (rf"pause(?: {_MY}(?:agent|worker|tasks))?", lambda m: _control("pause_agent")),
    (rf"(?:resume|unpause)(?: {_MY}(?:agent|worker|tasks))?", lambda m: _control("resume_agent")),
    (rf"(?:show |check |get )?(?:me )?{_MY}queue(?: status)?|what(?:'s| is) in {_MY}queue",
     lambda m: _control("queue_status")),
    (rf"stop(?: {_MY}(?:current |running )?task)?|stop (?:it|everything|that)|cancel {_MY}current task",
     lambda m: _control("stop_current_task")),
    (rf"(?:last|latest) (?:task|status|result)|(?:last|latest) task status|"
     rf"what happened (?:to|with) {_MY}last task",
     lambda m: _control("latest_status")),
    (rf"wake(?: up)? {_MY}{_PC}|wake {_MY}{_PC} up|turn on {_MY}{_PC}",
     lambda m: _control("wake_pc")),
    (rf"(?:take |send |get |grab )?(?:me )?(?:a )?(?:screenshot|screen shot|screen grab)"
     rf"(?: of {_MY}screen)?|ss",
     lambda m: _task("take_screenshot")),
    (rf"(?:run |send |get |show )?(?:me )?{_MY}daily report",
     lambda m: _task("run_named_script", script_name="daily_report")),
    (rf"(?:run |send |get |show )?(?:me )?{_MY}(?:stock|stocks)(?: report| prices)?",
     lambda m: _task("run_named_script", script_name="stock_report")),
    (rf"(?:clean ?up|clear|tidy(?: up)?) {_MY}downloads(?: folder)?",
     lambda m: _task("run_named_script", script_name="cleanup_downloads", requires_approval=True)),
    (rf"(?:list|show)(?: me)?(?: the)? files (?:in|on) {_MY}(?P<folder>downloads|desktop)(?: folder)?|"
     rf"(?:what's|what is) (?:in|on) {_MY}(?P<folder2>downloads|desktop)(?: folder)?",
     lambda m: _task("list_files_in_folder", folder_path=m.group("folder") or m.group("folder2"))),
    # Bare domains only: paths are case-sensitive and the text is lowercased.
    (r"open (?P<url>(?:https?://)?[a-z0-9-]+(?:\.[a-z0-9-]+)+/?)",
     lambda m: _task("open_url", url=_with_scheme(m.group("url")))),
]

_COMPILED = [(re.compile(pattern), build) for pattern, build in _RULES]

def _with_scheme(url: str) -> str:
    return url if url.startswith(("http://", "https://")) else f"https://{url}"

def match_quick_command(user_text: str) -> PlannerDecision | None:
    text = _normalize(user_text)
    for pattern, build in _COMPILED:
        match = pattern.fullmatch(text)
        if match:
            return build(match)
    return None
