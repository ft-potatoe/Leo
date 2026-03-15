"""
LLM client for Anthropic Claude API.

Provides:
- analyze_with_llm_json(): structured JSON responses for deep research
- call_claude_with_search(): agent analysis using web search tool
- Token usage tracking and cost estimation
- Graceful fallback when API key is missing
"""

import json
import os
import re
from datetime import datetime, timezone

try:
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv()
except ImportError:
    pass

try:
    import anthropic as _anthropic_module
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ── Token usage tracking ──────────────────────────────────────────────────────

_session_input_tokens: int = 0
_session_output_tokens: int = 0

# Pricing per million tokens (as of claude-opus-4-5)
_PRICING = {
    "claude-opus-4-5": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-5": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.0},
}
_DEFAULT_MODEL = "claude-opus-4-5"

# ── Client singleton ──────────────────────────────────────────────────────────

_client = None


def _get_client():
    global _client
    if not _ANTHROPIC_AVAILABLE:
        return None
    if _client is None:
        _client = _anthropic_module.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def is_llm_available() -> bool:
    """Return True if the Anthropic API key is configured and library is installed."""
    return _ANTHROPIC_AVAILABLE and bool(ANTHROPIC_API_KEY)


# ── Web search tool definition ────────────────────────────────────────────────

# Anthropic native web search tool (web_search_20250305)
WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
}


# ── Core LLM helpers ─────────────────────────────────────────────────────────

def _strip_markdown_json(text: str) -> str:
    """Remove ```json ... ``` wrappers if present."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def _accumulate_tokens(input_tokens: int, output_tokens: int) -> None:
    global _session_input_tokens, _session_output_tokens
    _session_input_tokens += input_tokens
    _session_output_tokens += output_tokens


def _estimate_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    rates = _PRICING.get(model, _PRICING[_DEFAULT_MODEL])
    return (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000


async def analyze_with_llm_json(
    system_prompt: str,
    user_prompt: str,
    model: str = _DEFAULT_MODEL,
) -> dict:
    """
    Call Claude and return a parsed JSON dict.
    Used by DeepResearchEngine for sub-query decomposition and cross-referencing.
    Returns {} on any error.
    """
    if not is_llm_available():
        return {}

    client = _get_client()
    if client is None:
        return {}

    try:
        message = await client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt + "\n\nCRITICAL: Respond ONLY with valid JSON. No markdown, no code fences, no explanation.",
            messages=[{"role": "user", "content": user_prompt}],
        )
        _accumulate_tokens(message.usage.input_tokens, message.usage.output_tokens)
        raw = message.content[0].text if message.content else ""
        return json.loads(_strip_markdown_json(raw))
    except Exception:
        return {}


async def call_claude_with_search(
    system_prompt: str,
    user_prompt: str,
    model: str = _DEFAULT_MODEL,
    max_tokens: int = 4096,
    use_web_search: bool = True,
) -> tuple[str, list[dict], dict]:
    """
    Call Claude with optional native web search tool.

    Returns:
        (text_response, tool_uses, usage_dict)
        - text_response: final text from Claude
        - tool_uses: list of {"tool_name", "input"} dicts for any tool calls made
        - usage_dict: {"input_tokens", "output_tokens", "estimated_cost_usd"}
    """
    if not is_llm_available():
        return "", [], {}

    client = _get_client()
    if client is None:
        return "", [], {}

    tools = [WEB_SEARCH_TOOL] if use_web_search else []

    try:
        kwargs: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        if tools:
            kwargs["tools"] = tools

        message = await client.messages.create(**kwargs)
        _accumulate_tokens(message.usage.input_tokens, message.usage.output_tokens)

        text_parts: list[str] = []
        tool_uses: list[dict] = []

        for block in message.content:
            if hasattr(block, "text"):
                text_parts.append(block.text)
            elif hasattr(block, "type") and block.type == "tool_use":
                tool_uses.append({
                    "tool_name": block.name,
                    "input": block.input,
                    "id": block.id,
                })

        usage = {
            "input_tokens": message.usage.input_tokens,
            "output_tokens": message.usage.output_tokens,
            "estimated_cost_usd": _estimate_cost(
                message.usage.input_tokens, message.usage.output_tokens, model
            ),
        }

        return " ".join(text_parts), tool_uses, usage

    except Exception:
        return "", [], {}


async def analyze_search_results_with_claude(
    agent_name: str,
    system_prompt: str,
    query: str,
    search_results: list[dict],
    model: str = _DEFAULT_MODEL,
) -> dict:
    """
    Feed collected search results to Claude for structured intelligence extraction.

    Returns a dict matching the agent output schema:
    {
      "agentId": str,
      "confidence": "high"|"medium"|"low",
      "findings": [{"statement", "type", "confidence", "rationale"}],
      "sources": [{"url", "title", "snippet"}],
      "facts": [str],
      "interpretations": [str],
    }
    """
    if not is_llm_available() or not search_results:
        return {}

    # Summarize search results for Claude
    results_text = "\n\n".join(
        f"[Source {i+1}] {r.get('title', 'Untitled')}\nURL: {r.get('url', '')}\nSnippet: {r.get('snippet', '')}"
        for i, r in enumerate(search_results[:10])
    )

    user_prompt = f"""Query: {query}

Search Results:
{results_text}

Analyze these search results and return structured intelligence in this exact JSON format:
{{
  "agentId": "{agent_name}",
  "confidence": "high|medium|low",
  "findings": [
    {{
      "statement": "specific factual or interpretive finding",
      "type": "fact|interpretation|recommendation",
      "confidence": "high|medium|low",
      "rationale": "why you believe this based on the sources"
    }}
  ],
  "sources": [
    {{
      "url": "source url",
      "title": "source title",
      "snippet": "relevant excerpt"
    }}
  ],
  "facts": ["list of direct factual claims"],
  "interpretations": ["list of analytical interpretations"]
}}

Generate 3-6 findings. Be specific, grounded in the sources, and clearly separate facts from interpretations."""

    result = await analyze_with_llm_json(system_prompt, user_prompt, model)
    return result


# ── Session cost tracking ─────────────────────────────────────────────────────

def get_session_token_usage() -> dict:
    """Return cumulative token usage and cost for the current session."""
    return {
        "total_input_tokens": _session_input_tokens,
        "total_output_tokens": _session_output_tokens,
        "total_tokens": _session_input_tokens + _session_output_tokens,
        "estimated_cost_usd": round(
            _estimate_cost(_session_input_tokens, _session_output_tokens, _DEFAULT_MODEL), 6
        ),
        "model": _DEFAULT_MODEL,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def reset_session_token_usage() -> None:
    """Reset session token counters (call at start of each request if desired)."""
    global _session_input_tokens, _session_output_tokens
    _session_input_tokens = 0
    _session_output_tokens = 0
