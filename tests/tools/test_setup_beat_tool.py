"""``setup_beat`` through the agent's inline executor, with a real session store and a fake card
answer standing in for the desktop."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from agent import onboarding_record
from agent.inline_tool_executors import INLINE_TOOL_EXECUTORS, InlineToolContext
from agent.onboarding_flow import Facts, SkipAll
from hermes_state import SessionDB
from tools.registry import registry

SID = "onb-session"
FACTS = Facts(os="macos", arch="arm64", machine_kind="Mac", plugins=("blender",))


@pytest.fixture
def db(tmp_path, monkeypatch):
    # The run's start and end write the install flag in the root config; that is not under test here.
    monkeypatch.setattr("hermes_cli.onboarding_run.set_run", lambda *a, **k: None)
    store = SessionDB(db_path=tmp_path / "state.db")
    store.create_session(SID, "desktop")
    yield store
    store.close()


@pytest.fixture
def desktop():
    """A card answerer: replies come off a queue; every payload it was shown is kept."""
    shown, replies = [], []

    def answer(payload):
        shown.append(payload)
        return replies.pop(0) if replies else None
    return SimpleNamespace(shown=shown, replies=replies, answer=answer)


def call(db, desktop, call_id="call_1", **args):
    agent = SimpleNamespace(_session_db=db, session_id=SID, setup_beat_callback=desktop.answer)
    return json.loads(INLINE_TOOL_EXECUTORS["setup_beat"](agent, args, InlineToolContext("task", call_id)))


def test_a_card_answer_settles_the_beat_and_names_the_next(db, desktop):
    onboarding_record.start(db, SID, FACTS)
    desktop.replies.append({"answer": {"accent": "Ultraviolet"}})

    result = call(db, desktop, beat="theme", question="Pick one.")

    assert desktop.shown == [{"beat": "theme", "question": "Pick one.", "card": {"picker": "accent"}}]
    assert result["answer"] == {"accent": "Ultraviolet"} and result["next"] == "name"
    assert "Ultraviolet" in result["reminder"]
    assert onboarding_record.load(db, SID)["beats"]["theme"] == "done"


def test_next_shows_the_first_open_beat_and_the_name_card_offers_the_account_name(db, desktop, monkeypatch):
    monkeypatch.setattr("agent.onboarding_facts.suggested_name", lambda: "Ada Lovelace")
    onboarding_record.start(db, SID, FACTS)
    desktop.replies.append({"said": "Ada"})

    result = call(db, desktop, beat="next")

    assert desktop.shown[0]["beat"] == "name" and desktop.shown[0]["card"] == {"suggested": "Ada Lovelace"}
    # Words typed while the name card waits are the name; the account name reaches the model only if picked.
    assert result["answer"] == {"name": "Ada"} and "Ada Lovelace" not in json.dumps(result)


def test_no_answer_closes_the_card_and_typed_words_come_back_as_said(db, desktop):
    onboarding_record.start(db, SID, FACTS)
    timed_out = call(db, desktop, beat="layout")
    desktop.replies.append({"said": "what is Elite?"})
    said = call(db, desktop, beat="layout", call_id="call_2")

    assert timed_out["timed_out"] is True and "five minutes" in timed_out["reminder"]
    assert said["said"] == "what is Elite?" and 'setup_beat(beat="layout")' in said["reminder"]
    assert onboarding_record.load(db, SID)["waiting"] is None


def test_suggest_pins_connectors_and_value_or_skip_records_without_a_card(db, desktop):
    onboarding_record.start(db, SID, FACTS)
    desktop.replies.append({"answer": {"connected": ["slack"], "newly_connected": ["slack"]}})
    call(db, desktop, beat="connectors", suggest=["slack", "linear"])
    recorded = call(db, desktop, beat="tour", value="skip")
    skipped = call(db, desktop, beat="plugins", skip=True)

    assert desktop.shown[0]["card"] == {"suggested": ["slack", "linear"]} and len(desktop.shown) == 1
    assert recorded["recorded"] == "tour" and "No tour" in recorded["reminder"]
    assert skipped["skipped"] is True


def test_skip_setup_during_a_card_returns_skipped_all(db, desktop):
    onboarding_record.start(db, SID, FACTS)

    def skip_pressed(payload):
        onboarding_record.advance(db, SID, SkipAll())

    desktop.answer = skip_pressed
    result = call(db, desktop, beat="theme")

    assert result["skipped_all"] is True and "stop guiding" in result["reminder"]
    assert "error" in call(db, desktop, beat="next")


def test_done_ends_the_run_only_after_the_build_card(db, desktop):
    onboarding_record.start(db, SID, FACTS)
    refused = call(db, desktop, beat="done")
    # The model cannot end it early: a user who wants to stop is pointed at the Skip setup button.
    quit_in_words = call(db, desktop, beat="done", skip=True)
    assert "Skip setup" in quit_in_words["error"] and onboarding_record.load(db, SID)["phase"] == "onboarding"
    desktop.replies.append({"answer": {"build": "week"}})
    build = call(db, desktop, beat="build")
    done = call(db, desktop, beat="done")

    assert "error" in refused
    assert "How does this look?" in build["reminder"]
    assert done == {"completed": True, "reminder": done["reminder"]}
    assert onboarding_record.load(db, SID)["phase"] == "complete"


def test_outside_an_onboarding_chat_the_tool_refuses(db, desktop):
    assert "not running" in call(db, desktop, beat="next")["error"]
    # A bare registry dispatch has no session store or card callback.
    assert "error" in json.loads(registry.dispatch("setup_beat", {"beat": "next"}))
