import json
from typing import Any

from openai import OpenAI

from shared.config import LLM_API_KEY, LLM_BASE_URL

# Any OpenAI-compatible server works; the default is a local Ollama.
client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)

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
    return json.loads(response.choices[0].message.content)
