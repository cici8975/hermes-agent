"""First-run onboarding as data: the beats, the run record, and how each event moves the record.

Pure: no I/O, no clock. ``apply(record, event, facts, now=...)`` returns the next record, the result
the model reads, and the key of the reminder that rides on it (``agent/onboarding_text.py`` renders
it). The record is stored by ``agent/onboarding_record.py``; ``tools/setup_beat_tool.py`` drives it.
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
from typing import Any

PENDING, SHOWN, DONE, SKIPPED = "pending", "shown", "done", "skipped"
ONBOARDING, COMPLETE, PHASE_SKIPPED = "onboarding", "complete", "skipped"
CARD_TIMEOUT_S = 300
# Fallback end: no onboarding change for this long after the build card was reached.
QUIET_COMPLETE_S = 30 * 60
MAX_PLUGINS = 5

LAYOUT_OPTIONS = ({"id": "sidebar-left", "label": "Basic"}, {"id": "terminal-deck", "label": "Elite"})
TOUR_OPTIONS = ({"id": "quick", "label": "Quick tour"}, {"id": "full", "label": "Show me everything"},
                {"id": "skip", "label": "Skip, let's build something"})


@dataclass(frozen=True)
class Facts:
    """The safe facts (class A) one run is built from. ``full_name`` reaches only the name card; it is
    never stored in the record or put in a result."""

    os: str  # macos | windows | linux
    arch: str = ""
    machine_kind: str = "computer"  # Mac | PC | Spark | computer
    nvidia_platform: str | None = None  # rtx_spark | dgx_spark | discrete
    facts_source: str = "local"  # local | remote: whose computer these facts describe
    locale: str | None = None
    plugins: tuple[str, ...] = ()  # onboarding catalog plugins this OS runs
    tours: bool = True
    full_name: str | None = field(default=None, compare=False)

    def stored(self) -> dict:
        data = asdict(self)
        data.pop("full_name")
        data["plugins"] = list(self.plugins)
        return data

    @classmethod
    def from_stored(cls, data: Mapping[str, Any]) -> Facts:
        known = {key: data[key] for key in cls.__dataclass_fields__ if key in data and key != "full_name"}
        return cls(**{**known, "plugins": tuple(known.get("plugins") or ())})


# ── events ────────────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Shown:
    beat: str
    tool_call_id: str = ""


@dataclass(frozen=True)
class Answered:
    beat: str
    answer: Mapping[str, Any]


@dataclass(frozen=True)
class Said:
    beat: str
    text: str


@dataclass(frozen=True)
class TimedOut:
    beat: str


@dataclass(frozen=True)
class Recorded:
    beat: str
    value: str


@dataclass(frozen=True)
class Skipped:
    beat: str


@dataclass(frozen=True)
class SkipAll:
    pass


@dataclass(frozen=True)
class Done:
    pass


@dataclass(frozen=True)
class Applied:
    """A general tool's result during the run: ``set_theme``, ``manage_connections`` display, ``gui_tour``."""

    tool: str
    args: Mapping[str, Any]
    result: Mapping[str, Any]


Event = Shown | Answered | Said | TimedOut | Recorded | Skipped | SkipAll | Done | Applied


@dataclass(frozen=True)
class Step:
    record: dict
    result: dict
    reminder: str = ""


# ── beats ─────────────────────────────────────────────────────────────────────────────────────


def build_options(facts: Facts, picks: Mapping[str, Any]) -> list[dict]:
    """Two tasks that fit the facts and picks, then the three fixed rows."""
    installed, connected = set(picks.get("installed") or ()), list(picks.get("connected") or ())
    tasks = [
        ("games", "Set up my games and streaming", facts.os == "windows" and facts.nvidia_platform == "discrete"),
        ("blender", "Help me make something in Blender", "blender" in installed),
        ("brief", "A daily brief from my apps", bool(connected)),
        ("week", "A summary of my week", True),
        ("scan", f"Look around this {facts.machine_kind} and suggest something", True),
    ]
    rows = [{"id": task_id, "label": label} for task_id, label, fits in tasks if fits][:2]
    return [*rows, {"id": "mind", "label": "I have something in mind"},
            {"id": "machine", "label": f"Help me set up this {facts.machine_kind}"},
            {"id": "together", "label": "Let's figure it out together"}]


def _option_ids(options) -> tuple[str, ...]:
    return tuple(option["id"] for option in options)


@dataclass(frozen=True)
class Beat:
    """``card`` is the beat's data for the desktop; ``when`` false skips the beat on this machine;
    ``picks`` are the answer keys recorded; ``value`` is the pick a ``value`` given in words sets
    (None: the beat takes no value, it is only marked done); ``values`` lists the accepted ids."""

    id: str
    card: Callable[[Facts, Mapping], dict]
    picks: tuple[str, ...]
    value: str | None = None
    values: Callable[[Facts, Mapping], tuple[str, ...]] | None = None
    when: Callable[[Facts, Mapping], bool] = lambda facts, picks: True

    def after(self, picks: Mapping[str, Any]) -> str:
        """Reminder key for the result that settles this beat."""
        if self.id in ("tour", "build") and picks.get(self.id):
            return f"{self.id}_{picks[self.id]}"
        return f"after_{self.id}"


BEATS: tuple[Beat, ...] = (
    Beat("name", lambda facts, picks: {}, picks=("name",), value="name"),
    Beat("theme", lambda facts, picks: {"picker": "accent"}, picks=("accent", "mode"), value="accent"),
    Beat("layout", lambda facts, picks: {"options": list(LAYOUT_OPTIONS)}, picks=("layout",), value="layout",
         values=lambda facts, picks: _option_ids(LAYOUT_OPTIONS)),
    Beat("connectors", lambda facts, picks: {}, picks=("connected", "newly_connected")),
    Beat("plugins", lambda facts, picks: {"plugins": list(facts.plugins[:MAX_PLUGINS])}, picks=("installed",),
         when=lambda facts, picks: bool(facts.plugins)),
    Beat("tour", lambda facts, picks: {"options": list(TOUR_OPTIONS)}, picks=("tour",), value="tour",
         values=lambda facts, picks: _option_ids(TOUR_OPTIONS), when=lambda facts, picks: facts.tours),
    Beat("build", lambda facts, picks: {"options": build_options(facts, picks)}, picks=("build",), value="build",
         values=lambda facts, picks: _option_ids(build_options(facts, picks))),
)
BEAT_BY_ID = {beat.id: beat for beat in BEATS}
BEAT_IDS = tuple(BEAT_BY_ID)


def new_record(facts: Facts, *, now: float = 0.0) -> dict:
    record = {
        "phase": ONBOARDING, "beats": {beat.id: PENDING for beat in BEATS}, "waiting": None,
        "picks": {"name": None, "accent": None, "mode": None, "layout": None, "connected": [],
                  "newly_connected": [], "installed": [], "tour": None, "build": None},
        "look_around": "not_offered", "facts": facts.stored(), "ended_by": None,
        "started_at": now, "updated_at": now,
    }
    return _settle_unfit(record, facts)


def _settle_unfit(record: dict, facts: Facts) -> dict:
    for beat in BEATS:
        if record["beats"][beat.id] == PENDING and not beat.when(facts, record["picks"]):
            record["beats"][beat.id] = SKIPPED
    return record


def next_beat(record: Mapping[str, Any]) -> str | None:
    """The first beat still pending or shown; None when every beat is settled."""
    return next((beat for beat in BEAT_IDS if record["beats"][beat] in (PENDING, SHOWN)), None)


def is_active(record: Mapping[str, Any] | None) -> bool:
    return bool(record) and record.get("phase") == ONBOARDING


def expire(record: dict, *, now: float) -> dict:
    """The quiet-spell fallback: a run whose build card was reached and that has not changed for
    ``QUIET_COMPLETE_S`` is complete."""
    if is_active(record) and record["beats"]["build"] != PENDING and now - record["updated_at"] >= QUIET_COMPLETE_S:
        record = copy.deepcopy(record)
        record.update(phase=COMPLETE, ended_by="timeout", waiting=None, updated_at=now)
    return record


# ── apply ─────────────────────────────────────────────────────────────────────────────────────


def _next_field(record: Mapping[str, Any]) -> str:
    return next_beat(record) or "done"


def _settle(record: dict, beat: str, patch: Mapping[str, Any]) -> None:
    record["beats"][beat] = DONE
    record["picks"].update({key: value for key, value in patch.items() if key in BEAT_BY_ID[beat].picks})


def _shown(record: dict, event: Shown, facts: Facts, now: float) -> Step:
    if not BEAT_BY_ID[event.beat].when(facts, record["picks"]):
        record["beats"][event.beat] = SKIPPED
        return Step(record, {"beat": event.beat, "skipped": True, "next": _next_field(record)},
                    f"after_{event.beat}")
    # A later card on screen means the user moved on from an earlier card left open.
    for earlier in BEAT_IDS[:BEAT_IDS.index(event.beat)]:
        if record["beats"][earlier] == SHOWN:
            record["beats"][earlier] = DONE
    if record["beats"][event.beat] != DONE:
        record["beats"][event.beat] = SHOWN
    if event.beat == "connectors" and record["look_around"] == "not_offered":
        record["look_around"] = "offered"
    record["waiting"] = {"beat": event.beat, "tool_call_id": event.tool_call_id, "since": now}
    return Step(record, {})


def _is_names(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def valid_answer(beat: str, answer: Mapping[str, Any], facts: Facts, picks: Mapping[str, Any]) -> bool:
    """A card answer carries only its beat's pick keys, with ids from the card's own options."""
    spec = BEAT_BY_ID[beat]
    if not answer or not set(answer) <= set(spec.picks):
        return False
    if spec.values is not None:
        return answer.get(spec.value) in spec.values(facts, picks)
    if beat == "name":
        return isinstance(answer.get("name"), str) and bool(answer["name"].strip())
    if beat == "theme":
        return all(value is None or isinstance(value, str) for value in answer.values())
    if beat == "plugins":
        return _is_names(answer.get("installed")) and set(answer["installed"]) <= set(facts.plugins)
    return "connected" in answer and all(_is_names(value) for value in answer.values())


def _answered(record: dict, event: Answered, facts: Facts, now: float) -> Step:
    record["waiting"] = None
    if not valid_answer(event.beat, event.answer, facts, record["picks"]):
        return Step(record, {"beat": event.beat, "error": "The card sent an answer this beat does not accept. "
                             f'Bring it back with setup_beat(beat="{event.beat}").'})
    _settle(record, event.beat, event.answer)
    return Step(record, {"beat": event.beat, "answer": dict(event.answer), "next": _next_field(record)},
                BEAT_BY_ID[event.beat].after(record["picks"]))


def _said(record: dict, event: Said, facts: Facts, now: float) -> Step:
    record["waiting"] = None
    return Step(record, {"beat": event.beat, "said": event.text}, "said")


def _timed_out(record: dict, event: TimedOut, facts: Facts, now: float) -> Step:
    record["waiting"] = None
    return Step(record, {"beat": event.beat, "timed_out": True}, "timed_out")


def _recorded(record: dict, event: Recorded, facts: Facts, now: float) -> Step:
    beat = BEAT_BY_ID[event.beat]
    accepted = beat.values(facts, record["picks"]) if beat.values else None
    if accepted is not None and event.value not in accepted:
        return Step(record, {"error": f"value for {event.beat} must be one of: {', '.join(accepted)}.",
                             "next": _next_field(record)})
    _settle(record, event.beat, {beat.value: event.value} if beat.value else {})
    return Step(record, {"recorded": event.beat, "next": _next_field(record)}, beat.after(record["picks"]))


def _skipped(record: dict, event: Skipped, facts: Facts, now: float) -> Step:
    record["beats"][event.beat] = SKIPPED
    return Step(record, {"recorded": event.beat, "skipped": True, "next": _next_field(record)}, "moved_on")


def _skip_all(record: dict, event: SkipAll, facts: Facts, now: float) -> Step:
    record.update(phase=PHASE_SKIPPED, ended_by="skip", waiting=None)
    for beat in BEAT_IDS:
        if record["beats"][beat] != DONE:
            record["beats"][beat] = SKIPPED
    return Step(record, {"skipped_all": True}, "skip_all")


def _done(record: dict, event: Done, facts: Facts, now: float) -> Step:
    if record["beats"]["build"] == PENDING:
        return Step(record, {"error": "Onboarding ends after the first build is shown and its close card is "
                                      "answered. If they want to stop, tell them about the Skip setup button.",
                             "next": _next_field(record)})
    record["beats"]["build"] = DONE
    record.update(phase=COMPLETE, ended_by="done", waiting=None)
    return Step(record, {"completed": True}, "complete")


def _applied_beats(event: Applied) -> list[tuple[str, dict]]:
    """The beats a general tool's result settles, with the picks it recorded."""
    result, args = event.result, event.args
    if event.tool == "set_theme":
        values = result.get("applied") or result.get("picked") or {}
        theme = {key: values[key] for key in ("accent", "mode") if key in values}
        settled = [("theme", theme)] if theme else []
        return [*settled, ("layout", {"layout": values["layout"]})] if values.get("layout") else settled
    if event.tool == "manage_connections" and args.get("action") == "display" and "connected" in result:
        return [("connectors", {"connected": list(result.get("connected") or ()),
                                "newly_connected": list(result.get("newly_connected") or ())})]
    if event.tool == "gui_tour" and args.get("action") == "start" and not result.get("error"):
        return [("tour", {"tour": args.get("preset") or "full"})]
    return []


def _applied(record: dict, event: Applied, facts: Facts, now: float) -> Step:
    for beat, patch in _applied_beats(event):
        _settle(record, beat, patch)
    return Step(record, {})


_HANDLERS: dict[type, Callable[[dict, Any, Facts, float], Step]] = {
    Shown: _shown, Answered: _answered, Said: _said, TimedOut: _timed_out, Recorded: _recorded,
    Skipped: _skipped, SkipAll: _skip_all, Done: _done, Applied: _applied,
}
_ENDED = "Onboarding is over in this chat; it is a normal chat now."


def apply(record: Mapping[str, Any], event: Event, facts: Facts, *, now: float = 0.0) -> Step:
    """The record after ``event``, the model-facing result, and the reminder key. A finished run
    refuses every setup_beat event and ignores general tool results."""
    working = copy.deepcopy(dict(record))
    if not is_active(working):
        return Step(working, {} if isinstance(event, Applied) else {"error": _ENDED})
    step = _HANDLERS[type(event)](working, event, facts, now)
    if step.record != record:
        step.record["updated_at"] = now
    return step


def applies_to(tool: str) -> bool:
    """Whether a general tool's result can settle a beat (the hook's cheap pre-check)."""
    return tool in ("set_theme", "manage_connections", "gui_tour")
