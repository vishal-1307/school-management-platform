"""AI assistant request/response schemas.

The wire contract is plain-text transcript turns only — never raw Anthropic
``tool_use``/``tool_result`` content blocks. The backend reconstructs the
full Anthropic messages array itself on every call.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TranscriptTurn(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    text: str


class ChatRequest(BaseModel):
    transcript: list[TranscriptTurn] = Field(..., min_length=1)


class PendingActionSchema(BaseModel):
    action_id: str
    title: str
    summary: str
    preview: Any = None


class ChatResponse(BaseModel):
    reply: str
    pending_action: PendingActionSchema | None = None


class ConfirmRequest(BaseModel):
    action_id: str


class ConfirmResponse(BaseModel):
    reply: str


class CancelRequest(BaseModel):
    action_id: str
