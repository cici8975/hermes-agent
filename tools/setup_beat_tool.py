"""``setup_beat``: the one onboarding-only tool. It shows a beat's card through the desktop, waits
for the user (``CARD_TIMEOUT_S``), and returns their answer with a short reminder of the next beat.

The ``onboarding`` toolset carrying it is folded in only for the onboarding chat, at agent build
(``tui_gateway/methods_onboarding.py``). The run record is the session's ``onboarding_run``
(``agent/onboarding_record.py``); the order and the options are ``agent/onboarding_flow.py``.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any

from agent import onboarding_flow as flow
from agent.onboarding_text import QUESTIONS, finish_reminder, reminder
from tools.registry import registry, tool_error

BEATS = ("next", *flow.BEAT_IDS, "done")


def _direct_event(beat: str, args: Mapping[str, Any]) -> flow.Event | None:
    """An event the call carries in itself (no card): done, a value given in words, or a skip. Only the
    Skip setup button (onboarding.skip) ends onboarding early; the model never decides the user quit."""
    if beat == "done":
        return flow.Done()
    if args.get("skip"):
        return flow.Skipped(beat)
    value = args.get("value")
    return flow.Recorded(beat, value.strip()) if isinstance(value, str) and value.strip() else None


def _reply_event(beat: str, reply: Mapping[str, Any] | None) -> flow.Event:
    reply = reply or {}
    said = reply.get("said")
    if isinstance(said, str) and said.strip():
        # Words typed while the name card waits are the name, like its own text box.
        return flow.Answered(beat, {"name": said.strip()}) if beat == "name" else flow.Said(beat, said.strip())
    answer = reply.get("answer")
    return flow.Answered(beat, answer) if isinstance(answer, dict) and answer else flow.TimedOut(beat)


def _result(step: flow.Step, beat: str | None = None) -> str:
    facts = flow.Facts.from_stored(step.record["facts"])
    text = reminder(step.reminder, step.record, facts, beat)
    return json.dumps({**step.result, **({"reminder": text} if text else {})}, ensure_ascii=False)


def _card(beat: str, step: flow.Step, args: Mapping[str, Any]) -> dict:
    facts = flow.Facts.from_stored(step.record["facts"])
    card = flow.BEAT_BY_ID[beat].card(facts, step.record["picks"])
    if beat == "name":
        from agent.onboarding_facts import suggested_name

        # The account name goes to the card only; the model reads it if the user picks it.
        card = {"suggested": name} if (name := suggested_name()) else {}
    if beat == "connectors":
        card = {"suggested": [str(slug) for slug in args.get("suggest") or () if str(slug).strip()]}
    return card


def setup_beat_tool(args: Mapping[str, Any], *, db=None, session_id: str = "", tool_call_id: str = "",
                    callback: Callable[[dict], dict | None] | None = None) -> str:
    """``callback(payload) -> {answer?, said?} | {timed_out: true} | None`` asks the desktop to show
    ``{beat, question, card}`` and blocks until the user answers or the card closes."""
    from agent import onboarding_record as records

    beat = args.get("beat")
    if beat not in BEATS:
        return tool_error(f"beat must be one of: {', '.join(BEATS)}.")
    record = records.load(db, session_id)
    if record is None:
        return tool_error("Onboarding is not running in this chat.")
    if beat != "next" and (event := _direct_event(beat, args)) is not None:
        return _result(records.advance(db, session_id, event))
    if beat == "next":
        beat = flow.next_beat(record) if flow.is_active(record) else None
        if beat is None:
            return json.dumps({"next": "done", "reminder": finish_reminder(record)} if flow.is_active(record)
                              else {"error": "Onboarding is over in this chat; it is a normal chat now."})
    if callback is None:
        return tool_error("setup_beat cards show only in the Hermes desktop app.")
    shown = records.advance(db, session_id, flow.Shown(beat, tool_call_id))
    if shown.result:  # refused, or a beat this machine skips
        return _result(shown)
    question = str(args.get("question") or "").strip() or QUESTIONS[beat]
    reply = callback({"beat": beat, "question": question, "card": _card(beat, shown, args)})
    after = records.load(db, session_id)
    if after is not None and after["phase"] == flow.PHASE_SKIPPED:
        # Skip setup closed the card (onboarding.skip already wrote the record).
        return _result(flow.Step(after, {"skipped_all": True}, "skip_all"))
    return _result(records.advance(db, session_id, _reply_event(beat, reply)), beat)


SETUP_BEAT_SCHEMA = {
    "name": "setup_beat",
    "description": (
        "Run the first-run onboarding in this chat. Shows the card for a beat and waits for the user, then "
        "returns their answer and what to do next. beat=next shows the next beat. Pass value to record an answer "
        "they gave in words, skip to record that they skipped a beat. beat=done ends onboarding after the first "
        "build is shown and its close card is answered. Nothing here ends it early: a user who wants to stop "
        "presses Skip setup."
    ),
    "parameters": {
        "type": "object",
        "required": ["beat"],
        "properties": {
            "beat": {"type": "string", "enum": list(BEATS)},
            "question": {"type": "string", "description": "Your line above the card. The app fixes the options."},
            "value": {"type": "string", "description": "Record an answer given in words (a name, or an option id). No card."},
            "skip": {"type": "boolean", "description": "They skipped this beat in words. No card."},
            "suggest": {"type": "array", "items": {"type": "string"},
                        "description": "connectors only: slugs pinned as Suggested."},
        },
    },
}


registry.register(
    name="setup_beat", toolset="onboarding", schema=SETUP_BEAT_SCHEMA,
    # The agent loop runs it inline with the session's record and card callback
    # (agent/inline_tool_executors.py); a bare registry dispatch has neither.
    handler=lambda args, **kw: setup_beat_tool(args),
    emoji="🎛",
)
