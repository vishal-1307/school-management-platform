"""Async client for the model backend, normalized to one internal shape.

``run_messages`` always speaks the same contract to its callers regardless
of which provider is behind it: it accepts Anthropic-shaped ``messages``
(role + either a plain string or a list of ``text``/``tool_use``/
``tool_result`` blocks) and Anthropic-shaped ``tools`` (``name`` +
``description`` + ``input_schema``), and always returns a normalized
``{"stop_reason": "tool_use" | "end_turn", "content": [...]}``.

Two wire formats are supported, picked by ``settings.ai_wire_format``:

  - ``"openai"`` (default) — DigitalOcean Serverless Inference's
    OpenAI-compatible ``/v1/chat/completions`` endpoint, ``Authorization:
    Bearer`` auth, OpenAI function-calling tool_calls shape. This is what
    DeepSeek/GLM/Llama/GPT-* models on the platform require — Anthropic
    models are also listed in DO's catalog but may not be entitled on every
    account's subscription tier, which is why this is the default.
  - ``"anthropic"`` — DigitalOcean's Anthropic-compatible ``/v1/messages``
    endpoint (or a direct Anthropic API key), ``x-api-key`` +
    ``anthropic-version`` auth, native Anthropic Messages API shape.

Swapping provider/model later is a config change only (``AI_BASE_URL``,
``AI_MODEL``, ``AI_WIRE_FORMAT``, and the key) — ``assistant.py`` and
``tools.py`` never see the difference.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import settings

ANTHROPIC_VERSION = "2023-06-01"
_TIMEOUT = httpx.Timeout(60.0, connect=10.0)


class AIUnavailable(Exception):
    """Raised when the model API is unreachable, times out, or 5xxs."""


def _to_openai_messages(system: str, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    openai_messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
    for msg in messages:
        role = msg["role"]
        content = msg["content"]

        if isinstance(content, str):
            openai_messages.append({"role": role, "content": content})
            continue

        if role == "assistant":
            text = " ".join(b["text"] for b in content if b.get("type") == "text")
            tool_use_blocks = [b for b in content if b.get("type") == "tool_use"]
            assistant_msg: dict[str, Any] = {"role": "assistant", "content": text}
            if tool_use_blocks:
                assistant_msg["tool_calls"] = [
                    {
                        "id": b["id"],
                        "type": "function",
                        "function": {"name": b["name"], "arguments": json.dumps(b.get("input", {}))},
                    }
                    for b in tool_use_blocks
                ]
            openai_messages.append(assistant_msg)
        else:
            # Anthropic bundles tool_result blocks into one "user" message;
            # OpenAI wants one standalone "tool" message per result instead.
            for block in content:
                if block.get("type") == "tool_result":
                    openai_messages.append({
                        "role": "tool",
                        "tool_call_id": block["tool_use_id"],
                        "content": block.get("content", ""),
                    })
    return openai_messages


def _to_openai_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {"name": t["name"], "description": t["description"], "parameters": t["input_schema"]},
        }
        for t in tools
    ]


def _from_openai_response(data: dict[str, Any]) -> dict[str, Any]:
    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message", {}) or {}
    tool_calls = message.get("tool_calls") or []

    content: list[dict[str, Any]] = []
    text = message.get("content")
    if text:
        content.append({"type": "text", "text": text})
    for call in tool_calls:
        function = call.get("function", {})
        try:
            args = json.loads(function.get("arguments") or "{}")
        except json.JSONDecodeError:
            args = {}
        content.append({"type": "tool_use", "id": call["id"], "name": function.get("name"), "input": args})

    return {"stop_reason": "tool_use" if tool_calls else "end_turn", "content": content}


async def _post(url: str, body: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(url, json=body, headers=headers)
    except httpx.HTTPError as exc:
        raise AIUnavailable(f"AI assistant network error: {exc}") from exc

    if response.status_code >= 500:
        raise AIUnavailable(f"AI assistant upstream error: HTTP {response.status_code}")
    if response.status_code >= 400:
        raise AIUnavailable(
            f"AI assistant rejected the request: HTTP {response.status_code} {response.text[:300]}"
        )
    return response.json()


async def run_messages(
    system: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    max_tokens: int = 1024,
) -> dict[str, Any]:
    """Run one model turn. Returns a normalized {stop_reason, content} dict.

    Raises AIUnavailable on missing config, network errors, timeouts, or
    4xx/5xx responses so the router can surface one friendly message.
    """
    if not settings.do_model_access_key:
        raise AIUnavailable("AI assistant is not configured (DO_MODEL_ACCESS_KEY unset)")

    if settings.ai_wire_format == "anthropic":
        body = {
            "model": settings.ai_model, "max_tokens": max_tokens,
            "system": system, "messages": messages, "tools": tools,
        }
        headers = {
            "x-api-key": settings.do_model_access_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        return await _post(settings.ai_base_url, body, headers)

    # OpenAI-compatible wire format.
    body: dict[str, Any] = {
        "model": settings.ai_model,
        "max_tokens": max_tokens,
        "messages": _to_openai_messages(system, messages),
    }
    if tools:
        body["tools"] = _to_openai_tools(tools)
        body["tool_choice"] = "auto"
    headers = {
        "Authorization": f"Bearer {settings.do_model_access_key}",
        "Content-Type": "application/json",
    }
    data = await _post(settings.ai_base_url, body, headers)
    return _from_openai_response(data)
