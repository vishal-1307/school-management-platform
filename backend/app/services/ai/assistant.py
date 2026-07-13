"""Tool-use orchestration loop for the role-scoped AI assistant.

The wire contract with the frontend is plain-text transcript turns only —
never raw ``tool_use``/``tool_result`` blocks — so this module reconstructs
a fresh Anthropic ``messages`` array every call and runs the whole tool loop
server-side. READ tools execute immediately; a WRITE tool's ``preview`` is
read-only, and a "ready" result halts the loop and returns a pending action
for the client to Confirm/Cancel (see ``app/services/ai/pending.py``).
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.services.ai import pending
from app.services.ai.client import run_messages
from app.services.ai.tools import get_tool, get_tools_for_role

_MAX_TOOL_ROUNDS = 8


def _system_prompt(role: UserRole) -> str:
    common = (
        "You are the in-portal assistant for a school management platform. "
        "Only use the tools provided to you — never invent data. If a tool result has "
        "status 'ambiguous', list the options it gives you and ask the user to pick one; "
        "never guess which one they meant. If a tool result has status 'forbidden' or "
        "'error', or an 'error' key, tell the user plainly what happened — do not retry "
        "with different arguments to work around it."
    )
    if role in (UserRole.SUPER_ADMIN, UserRole.OFFICE_ADMIN):
        return common + (
            " You are speaking with a school administrator. For any write action "
            "(deactivating a student or staff member, reactivating a student, resetting a "
            "password), call the tool once — the app shows the user a confirmation card "
            "automatically and the action will not run until they click Confirm, so you do "
            "not need to separately ask 'are you sure'. Resolve a name to an id with "
            "search_people first if more than one person could match."
        )
    if role == UserRole.TEACHER:
        return common + (
            " You are speaking with a teacher. They can only see their own assigned classes "
            "and students. If a tool reports they are not assigned to a class/student, tell "
            "them that plainly rather than trying another way to fetch it. For "
            "mark_class_attendance, if they teach more than one class/section and don't say "
            "which, the tool returns status 'ambiguous' with the options — ask them to pick one."
        )
    return common + (
        " You are speaking with a student, about their OWN data only — every tool here is "
        "already scoped to them and cannot look up another student. If asked about another "
        "student, explain you can only help with their own information. Never claim an exam "
        "result exists unless the results tool actually returned it — an unpublished result "
        "must never be described, even if asked directly."
    )


def _stringify(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, default=str)


async def run_assistant(
    db: AsyncSession,
    current_user: User,
    transcript: list[dict],
    background_tasks: BackgroundTasks,
) -> dict:
    """Run the tool-use loop for one chat turn. Never mutates by itself."""
    tools = get_tools_for_role(current_user.role)
    anthropic_tools = [t.to_anthropic() for t in tools]
    system = _system_prompt(current_user.role)
    messages: list[dict] = [{"role": t["role"], "content": t["text"]} for t in transcript]

    for _ in range(_MAX_TOOL_ROUNDS):
        response = await run_messages(system, messages, anthropic_tools)
        content = response.get("content", [])

        if response.get("stop_reason") != "tool_use":
            reply = "".join(b.get("text", "") for b in content if b.get("type") == "text")
            return {"reply": reply.strip() or "OK."}

        messages.append({"role": "assistant", "content": content})
        tool_results: list[dict] = []
        pending_action_payload: dict | None = None

        for block in content:
            if block.get("type") != "tool_use":
                continue

            tool = get_tool(current_user.role, block["name"])
            args = block.get("input") or {}

            if tool is None:
                tool_results.append({
                    "type": "tool_result", "tool_use_id": block["id"],
                    "content": "That tool is not available for your role.", "is_error": True,
                })
                continue

            if not tool.is_write:
                try:
                    result = await tool.read(db, current_user, args)
                except Exception:
                    tool_results.append({
                        "type": "tool_result", "tool_use_id": block["id"],
                        "content": "That request couldn't be completed.", "is_error": True,
                    })
                    continue
                tool_results.append({
                    "type": "tool_result", "tool_use_id": block["id"], "content": _stringify(result),
                })
                continue

            # Role gate BEFORE preview runs — mirrors the require_role() the
            # reused handler enforces, since the executor calls that handler
            # directly and bypasses its own FastAPI dependency. Never even
            # resolves names/ids for a role that couldn't run the write.
            if not tool.allows(current_user.role):
                tool_results.append({
                    "type": "tool_result", "tool_use_id": block["id"],
                    "content": "You don't have permission to perform that action.", "is_error": True,
                })
                continue

            try:
                preview = await tool.preview(db, current_user, args)
            except Exception:
                tool_results.append({
                    "type": "tool_result", "tool_use_id": block["id"],
                    "content": "That request couldn't be completed.", "is_error": True,
                })
                continue
            if preview.get("status") != "ready":
                tool_results.append({
                    "type": "tool_result", "tool_use_id": block["id"], "content": _stringify(preview),
                })
                continue

            action = pending.create(
                user_id=current_user.id,
                tool_name=tool.name,
                args=preview["resolved_args"],
                title=preview["title"],
                summary=preview["summary"],
                preview=preview["preview"],
                executor=tool.execute,
                required_roles=tool.write_roles,
            )
            pending_action_payload = {
                "action_id": action.action_id,
                "title": action.title,
                "summary": action.summary,
                "preview": action.preview,
            }
            # A "ready" write halts the loop right here — Phase 1 never
            # mutates and never makes another model call once a write is staged.
            break

        if pending_action_payload is not None:
            leading_text = "".join(b.get("text", "") for b in content if b.get("type") == "text").strip()
            return {
                "reply": leading_text or pending_action_payload["summary"],
                "pending_action": pending_action_payload,
            }

        messages.append({"role": "user", "content": tool_results})

    return {"reply": "I wasn't able to finish that — could you rephrase your question?"}


async def confirm_pending_action(
    db: AsyncSession, current_user: User, action_id: str, background_tasks: BackgroundTasks
) -> str | None:
    """Execute a previously staged write. Returns None if unknown/expired/not-owned/no-longer-permitted."""
    action = pending.get(action_id, current_user.id)
    if action is None:
        return None
    # Re-check role at confirm time, not just at proposal time — an account's
    # role or active status may have changed in between (get_current_user
    # already rejects a deactivated/token-revoked account before we get here;
    # this additionally covers a role downgrade that didn't deactivate them).
    if action.required_roles and current_user.role not in action.required_roles:
        pending.discard(action_id)
        return None
    pending.discard(action_id)
    try:
        return await action.executor(db, current_user, action.args, background_tasks)
    except Exception:
        return "That action couldn't be completed — please try again from the portal directly."


def cancel_pending_action(current_user: User, action_id: str) -> bool:
    action = pending.get(action_id, current_user.id)
    if action is None:
        return False
    pending.discard(action_id)
    return True
