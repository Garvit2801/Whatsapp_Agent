import json
import threading
from typing import Any

import requests
from openai import OpenAI

from shared.config import LLM_API_KEY, LLM_BASE_URL, LLM_KEEP_ALIVE

# Any OpenAI-compatible server works; the default is a local Ollama.
client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)

def _post_keep_alive(model: str) -> None:
    native_url = LLM_BASE_URL.rstrip("/").removesuffix("/v1") + "/api/generate"
    try:
        # Can take a while when the machine is swapping, hence the long timeout.
        requests.post(native_url, json={"model": model, "keep_alive": LLM_KEEP_ALIVE}, timeout=120)
    except requests.RequestException:
        pass

def _set_keep_alive(model: str) -> None:
    """Tell Ollama to unload the model after LLM_KEEP_ALIVE idle, to free RAM.

    Ollama's OpenAI-compatible endpoint ignores keep_alive, so this uses its
    native API, in the background so replies aren't delayed. A no-op for
    other servers.
    """
    if LLM_KEEP_ALIVE:
        threading.Thread(target=_post_keep_alive, args=(model,), daemon=True).start()

def structured_completion(
    model: str,
    name: str,
    schema: dict[str, Any],
    instructions: str,
    input_text: str,
) -> dict[str, Any]:
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": instructions},
            {"role": "user", "content": input_text},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": name, "strict": True, "schema": schema},
        },
    )
    _set_keep_alive(model)
    return json.loads(response.choices[0].message.content)
