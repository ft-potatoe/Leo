"""
Shared LLM client for all agents.
Uses Anthropic Claude API for reasoning over collected evidence.
"""

import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def is_llm_available() -> bool:
    return bool(ANTHROPIC_API_KEY)


async def analyze_with_llm(
    system_prompt: str,
    user_prompt: str,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 2048,
    temperature: float = 0.3,
) -> str:
    """Send a prompt to Claude and return the text response."""
    if not is_llm_available():
        return ""
    try:
        client = _get_client()
        message = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text
    except Exception as e:
        return f"[LLM error: {e}]"


async def analyze_with_llm_json(
    system_prompt: str,
    user_prompt: str,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 2048,
    temperature: float = 0.2,
) -> dict | list | None:
    """Send a prompt to Claude and parse the response as JSON."""
    if not is_llm_available():
        return None
    try:
        client = _get_client()
        message = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt + "\n\nYou MUST respond with valid JSON only. No markdown fences, no explanation — just the JSON object.",
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw = message.content[0].text.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()
        return json.loads(raw)
    except json.JSONDecodeError:
        return None
    except Exception:
        return None
