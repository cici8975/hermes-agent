"""``agent.runaway_mitigation``: the ② session downgrade and the ④ escalation after a guard trip.

``agent.repetition_guard`` only DETECTS a degenerate loop and aborts the turn. The mitigation
module adds two follow-ups, and both are session-scoped: the effort downgrade is applied at the
wire chokepoint and never to global config, and the 3rd trip inside the 24h window soft-archives
the session (messages kept) with a user-visible alert raised once. Every entry point is
fail-open, so mitigation can never be the reason a turn dies.
"""
import time

import pytest

from agent.runaway_mitigation import (
    ALERT_COPY,
    ESCALATE_AFTER,
    WINDOW_SECONDS,
    _downgraded,
    _local_strikes,
    downgrade_effort,
    downgrade_wire_reasoning,
    note_runaway,
    session_downgraded,
)


@pytest.fixture(autouse=True)
def _clean_module_state():
    """The in-process fallback registry is module-level: isolate every test from it."""
    _local_strikes.clear()
    _downgraded.clear()
    yield
    _local_strikes.clear()
    _downgraded.clear()


class _FakeSessionDB:
    """The three ``hermes_state_sessions`` methods the module touches."""

    def __init__(self, *, broken=False):
        self.config: dict = {}
        self.archived: list[tuple[str, bool]] = []
        self.broken = broken

    def get_session_model_config_value(self, session_id, key, default=None):
        self._maybe_blow_up()
        return self.config.get(key, default)

    def patch_session_model_config(self, session_id, patch):
        self._maybe_blow_up()
        self.config.update(patch)

    def set_session_archived(self, session_id, archived):
        self._maybe_blow_up()
        self.archived.append((session_id, archived))
        return True

    def _maybe_blow_up(self):
        if self.broken:
            raise RuntimeError("session db unavailable")


class _Agent:
    def __init__(self, session_id="sess-1", *, db=None, reasoning_config=None):
        self.session_id = session_id
        self._session_db = db
        self.reasoning_config = reasoning_config


class TestDowngradeEffort:
    @pytest.mark.parametrize("effort,expected", [
        ("ultra", "max"),
        ("high", "medium"),
        ("medium", "low"),
        ("minimal", None),  # the bottom of the ENABLED ladder has nothing weaker
        ("none", None),     # disabling reasoning is not a downgrade
        ("banana", None),
        ("", None),
        (None, None),
    ])
    def test_one_tier_weaker_or_none(self, effort, expected):
        assert downgrade_effort(effort) == expected


class TestNoteRunaway:
    def test_first_trip_arms_the_downgrade_without_escalating(self):
        db = _FakeSessionDB()
        agent = _Agent(db=db)

        assert session_downgraded(agent) is False
        result = note_runaway(agent, site="stop_path")

        assert result.count == 1
        assert result.downgraded is True
        assert result.escalated is False and result.alert == ""
        assert session_downgraded(agent) is True
        assert len(db.config["runaway_strikes"]) == 1
        assert db.archived == []

    def test_third_trip_in_the_window_soft_archives_and_alerts_once(self):
        db = _FakeSessionDB()
        agent = _Agent(db=db)

        assert note_runaway(agent, site="stop_path").count == 1
        second = note_runaway(agent, site="interrupt")
        assert (second.count, second.escalated) == (2, False)
        assert db.archived == []

        third = note_runaway(agent, site="stream:chat-content")
        assert third.escalated is True and third.count == ESCALATE_AFTER
        assert third.alert == ALERT_COPY
        assert db.archived == [("sess-1", True)]  # soft-hide, messages kept
        assert db.config["runaway_alerted"] is True

        fourth = note_runaway(agent, site="stop_path")
        assert fourth.escalated is True and fourth.alert == ""  # alerted once per session
        assert db.archived == [("sess-1", True)]  # never re-archived

    def test_trips_outside_the_window_do_not_count(self):
        db = _FakeSessionDB()
        stale = time.time() - WINDOW_SECONDS - 60
        db.config["runaway_strikes"] = [stale, stale]
        agent = _Agent(db=db)

        result = note_runaway(agent, site="stop_path")

        assert result.count == 1 and result.escalated is False
        assert db.config["runaway_strikes"] == [pytest.approx(time.time(), abs=5)]

    def test_broken_db_is_fail_open_and_falls_back_in_process(self):
        agent = _Agent(session_id="sess-broken", db=_FakeSessionDB(broken=True))

        result = note_runaway(agent, site="stop_path")

        assert result.count == 1 and result.escalated is False
        assert _local_strikes["sess-broken"]  # the in-process registry took over

    def test_missing_session_id_is_a_safe_no_op(self):
        result = note_runaway(_Agent(session_id="", db=None), site="stop_path")

        assert result.count == 1 and result.downgraded is False


class TestDowngradeWireReasoning:
    CFG = {"enabled": True, "effort": "high"}

    def test_untouched_until_the_session_trips(self):
        agent = _Agent(db=_FakeSessionDB(), reasoning_config=dict(self.CFG))

        assert downgrade_wire_reasoning(agent, dict(self.CFG)) == self.CFG

    def test_one_tier_lower_once_armed_without_mutating_agent_config(self):
        agent = _Agent(db=_FakeSessionDB(), reasoning_config=dict(self.CFG))
        note_runaway(agent, site="stop_path")

        sent = downgrade_wire_reasoning(agent, dict(self.CFG))

        assert sent == {"enabled": True, "effort": "medium"}
        assert agent.reasoning_config == self.CFG  # /model re-resolves from config
        assert agent._wire_reasoning_config == sent

    @pytest.mark.parametrize("cfg", [
        {"enabled": False, "effort": "high"},  # reasoning already off: nothing to lower
        {"enabled": True, "effort": "minimal"},  # at the floor
        None,
    ])
    def test_other_shapes_pass_through(self, cfg):
        agent = _Agent(db=_FakeSessionDB())
        note_runaway(agent, site="stop_path")

        assert downgrade_wire_reasoning(agent, cfg) == cfg
