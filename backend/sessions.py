"""
In-memory chat sessions with rolling summarization when message list grows.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import uuid

import anthropic

logger = logging.getLogger(__name__)

MAX_MESSAGES_BEFORE_COMPRESS = 24
KEEP_LAST_MESSAGES = 8
SUMMARY_MODEL = "claude-3-haiku-20240307"

_lock = threading.Lock()
_sessions: dict[str, dict] = {}

_summarizer = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def _content_to_plain_text(content) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return str(content)
    parts = []
    for block in content:
        if not isinstance(block, dict):
            continue
        t = block.get("type")
        if t == "text":
            parts.append(block.get("text", ""))
        elif t == "tool_use":
            parts.append(f"[tool:{block.get('name', '')}]")
        elif t == "tool_result":
            parts.append("[tool_result]")
    return " ".join(parts).strip()


def _format_messages_for_summary(messages: list) -> str:
    lines = []
    for m in messages:
        role = m.get("role", "")
        text = _content_to_plain_text(m.get("content"))
        lines.append(f"{role.upper()}: {text[:4000]}")
    return "\n\n".join(lines)


def _summarize_segment(transcript: str, prior_memory: str) -> str:
    prompt = f"""You compress support-chat history for a Vulcan OmniPro 220 welding agent.

Existing memory (may be empty):
{prior_memory or "(none)"}

New messages to fold in:
{transcript}

Write ONE updated summary (max ~600 words). Preserve: processes (MIG/TIG/stick), voltages,
amperages, duty cycle numbers, page references, polarity, safety warnings, and any unresolved
user issue. Omit greetings and filler. Use clear bullet-style paragraphs."""

    try:
        resp = _summarizer.messages.create(
            model=SUMMARY_MODEL,
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text.strip()
    except Exception as e:
        logger.warning("summarization_failed: %s", e)
        return (prior_memory + "\n\n" + transcript[:8000]).strip()


def get_or_create_session(session_id: str | None) -> tuple[str, dict]:
    with _lock:
        if session_id and session_id in _sessions:
            return session_id, _sessions[session_id]
        sid = str(uuid.uuid4())
        _sessions[sid] = {"messages": [], "memory": ""}
        return sid, _sessions[sid]


def compress_session_if_needed(session: dict) -> None:
    """Summarize oldest messages into session['memory'], keep recent tail."""
    msgs = session.get("messages") or []
    if len(msgs) <= MAX_MESSAGES_BEFORE_COMPRESS:
        return

    old = msgs[:-KEEP_LAST_MESSAGES]
    keep = msgs[-KEEP_LAST_MESSAGES:]
    transcript = _format_messages_for_summary(old)
    prior = session.get("memory") or ""
    session["memory"] = _summarize_segment(transcript, prior)
    session["messages"] = keep
    logger.info(
        "session_compressed kept=%s memory_chars=%s",
        len(keep),
        len(session["memory"]),
    )


def update_session_messages(session: dict, messages: list) -> None:
    session["messages"] = messages
    compress_session_if_needed(session)
