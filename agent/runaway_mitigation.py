"""Session-scoped mitigation after the repetition guard trips.

``agent.repetition_guard`` only DETECTS a degenerate repetition loop and aborts the turn. Two
follow-ups are added here:

* **② conditional downgrade** — once a session trips the guard, its requests go out one
  reasoning tier lower (:data:`agent.reasoning_effort.EFFORT_LADDER`) for the rest of the
  session. Applied at the wire chokepoint (``_reasoning_config_for_wire``), never to global
  config, and it evaporates when the session ends.
* **④ escalation** — the 3rd trip inside :data:`WINDOW_SECONDS` soft-archives the session
  (``sessions.archived``; messages are kept) and raises a user-visible alert, so a transcript
  that keeps re-seeding the loop stops being replayed.

Trip timestamps persist per session in the session's ``model_config`` JSON, so the 24h window
survives a gateway restart. Agents with no session DB (unit tests, ``object.__new__``) fall
back to an in-process registry. Every entry point is fail-open: mitigation must never be the
reason a turn dies.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any

from agent.reasoning_effort import EFFORT_LADDER

logger = logging.getLogger(__name__)

#: Levels a downgrade may land on. ``none`` disables reasoning outright and is never a
#: degradation target for an enabled ask — the same rule :func:`agent.reasoning_effort.clamp_effort`
#: applies (clamping ``minimal`` to ``none`` would silently switch thinking off).
_DOWNGRADE_LADDER = tuple(level for level in EFFORT_LADDER if level != "none")

#: A trip older than this does not count toward escalation.
WINDOW_SECONDS = 24 * 3600
#: Trips inside :data:`WINDOW_SECONDS` that trigger the soft-archive fallback.
ESCALATE_AFTER = 3
#: Session ``model_config`` keys this module owns.
_STRIKES_KEY = "runaway_strikes"
_ALERTED_KEY = "runaway_alerted"

#: User-visible alert raised once per session when ④ fires. The delivery layer renders it.
ALERT_COPY = (
    "⚠️ **Session Archived After Repeated Repetition Loops**\n\n"
    f"This session tripped the repetition guard {ESCALATE_AFTER} times within 24h. Its "
    "transcript was soft-archived (messages kept, hidden from the session list) and its "
    "reasoning effort was lowered one tier.\n\n"
    "→ Use `/new` to start a fresh session and leave the looped context behind."
)

_lock = threading.Lock()
#: Fallback strike registry for agents without a session DB: session_id -> [timestamps].
_local_strikes: dict[str, list[float]] = {}
#: Sessions currently carrying the ② downgrade. In-process by design: a downgrade is scoped to
#: the live session, and the persisted strikes re-arm it on the next trip after a restart.
_downgraded: set[str] = set()


@dataclass(frozen=True)
class RunawayMitigation:
    """Outcome of one guard trip."""

    site: str
    count: int
    downgraded: bool   # ② is armed for this session
    escalated: bool    # ④ fired on this trip
    alert: str = ""    # user-visible alert copy (④ only; "" when already alerted)


def downgrade_effort(effort: Any) -> str | None:
    """The effort level one step weaker than *effort*; ``None`` at the floor or for unknown input.

    ``none`` is never returned: disabling reasoning is not a downgrade (see
    :data:`_DOWNGRADE_LADDER`), so ``minimal`` — the bottom of the enabled ladder — has no
    weaker level and yields ``None``.
    """
    level = str(effort or "").strip().lower()
    if level not in _DOWNGRADE_LADDER:
        return None
    idx = _DOWNGRADE_LADDER.index(level)
    return _DOWNGRADE_LADDER[idx - 1] if idx > 0 else None


def _session_id(agent: Any) -> str:
    return str(getattr(agent, "session_id", "") or "")


def _read_strikes(agent: Any) -> list[float]:
    """Trip timestamps recorded for this session (DB-backed, in-process fallback)."""
    sid = _session_id(agent)
    if not sid:
        return []
    db = getattr(agent, "_session_db", None)
    if db is not None:
        try:
            raw = db.get_session_model_config_value(sid, _STRIKES_KEY, []) or []
            return [
                float(t) for t in raw
                if isinstance(t, (int, float)) and not isinstance(t, bool)
            ]
        except Exception:
            logger.debug("runaway: strike read failed for session %s", sid, exc_info=True)
    with _lock:
        return list(_local_strikes.get(sid, []))


def _write_strikes(agent: Any, stamps: list[float]) -> None:
    sid = _session_id(agent)
    if not sid:
        return
    db = getattr(agent, "_session_db", None)
    if db is not None:
        try:
            db.patch_session_model_config(sid, {_STRIKES_KEY: stamps})
            return
        except Exception:
            logger.debug("runaway: strike write failed for session %s", sid, exc_info=True)
    with _lock:
        _local_strikes[sid] = stamps


def session_downgraded(agent: Any) -> bool:
    """True while ② is armed for this session (in-process flag; O(1), no DB hit)."""
    sid = _session_id(agent)
    return bool(sid) and sid in _downgraded


def downgrade_wire_reasoning(agent: Any, cfg: Any) -> Any:
    """*cfg* with its effort one tier lower while ② is armed; unchanged otherwise.

    The wire chokepoint calls this so the downgrade reaches every transport without mutating
    ``agent.reasoning_config`` (a ``/model`` switch re-resolves that from config).
    """
    if not isinstance(cfg, dict) or cfg.get("enabled") is False or not session_downgraded(agent):
        return cfg
    lower = downgrade_effort(cfg.get("effort"))
    if lower is None:
        return cfg
    out = {**cfg, "effort": lower}
    agent._wire_reasoning_config = out
    return out


def note_runaway(agent: Any, *, site: str) -> RunawayMitigation:
    """Record one guard trip: arm ②, and fire ④ on the Nth trip in the window. Never raises."""
    try:
        return _note_runaway(agent, site=site)
    except Exception:
        logger.warning("runaway mitigation failed (site=%s)", site, exc_info=True)
        return RunawayMitigation(site=site, count=0, downgraded=False, escalated=False)


def _note_runaway(agent: Any, *, site: str) -> RunawayMitigation:
    now = time.time()
    stamps = [t for t in _read_strikes(agent) if now - t < WINDOW_SECONDS]
    stamps.append(now)
    _write_strikes(agent, stamps)
    sid = _session_id(agent)
    if sid:
        with _lock:
            _downgraded.add(sid)
    count = len(stamps)
    if count < ESCALATE_AFTER:
        return RunawayMitigation(site=site, count=count, downgraded=bool(sid), escalated=False)
    alert = _escalate(agent)
    return RunawayMitigation(
        site=site, count=count, downgraded=bool(sid), escalated=True, alert=alert,
    )


def _escalate(agent: Any) -> str:
    """④: soft-archive this session once and return the alert copy ("" when already alerted)."""
    sid = _session_id(agent)
    db = getattr(agent, "_session_db", None)
    if db is None or not sid:
        return ALERT_COPY
    try:
        if db.get_session_model_config_value(sid, _ALERTED_KEY, False):
            return ""
    except Exception:
        logger.debug("runaway: alerted-flag read failed for session %s", sid, exc_info=True)
    try:
        db.set_session_archived(sid, True)
    except Exception:
        logger.warning("runaway: soft-archive failed for session %s", sid, exc_info=True)
    try:
        db.patch_session_model_config(sid, {_ALERTED_KEY: True})
    except Exception:
        logger.debug("runaway: alerted-flag write failed for session %s", sid, exc_info=True)
    return ALERT_COPY
