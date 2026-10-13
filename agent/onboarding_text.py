"""The words of first-run onboarding: the scripted greeting, the opening prompt, and the reminder
that rides on every ``setup_beat`` result. Pure; ``reminder(key, record, facts)`` renders the key
``agent/onboarding_flow.py::apply`` returns.

The rules for the whole run live in the opening prompt (a hidden user turn, so the system prompt
stays byte-stable); reminders say only what was picked and what comes next.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agent.onboarding_flow import Facts, next_beat

CHAT_TITLE = "Getting started"
GREETING = "Hi, I'm Hermes. Let's set things up for you. Then we'll get something cool done."

QUESTIONS = {
    "name": "What should I call you?",
    "theme": "Pick a colour.",
    "layout": "Which layout?",
    "connectors": "Which apps should I work with?",
    "plugins": "Want any of these?",
    "tour": "Want a look around first?",
    "build": "Know what you'd like me to make?",
}

_SET_THEME = 'tool_call {"calls":[{"name":"set_theme","arguments":{"accent":"Ultraviolet"}}]}'
_TOUR_CALL = 'tool_call {"calls":[{"name":"gui_tour","arguments":{"action":"start","preset":"%s"}}]}'

PROFILE_DIMENSIONS = (
    ("agent experience", "new to AI apps / chat apps only / has used local agents / builds agents"),
    ("technical depth", "non-developer / tinkerer / developer"),
    ("creative work", "none / hobby / regular"),
    ("gaming", "none / casual / enthusiast"),
    ("local compute", "cloud only / small local models / strong local (Spark, large GPU or unified memory)"),
    ("work context", "personal / work / mixed"),
    ("machine role", "daily driver / dedicated AI box / remote server"),
)

_NVIDIA = {
    "rtx_spark": "It is an NVIDIA RTX Spark (Windows on Arm), built to run local models.",
    "dgx_spark": "It is an NVIDIA DGX Spark (Linux on Arm with a GB10), built to run local models.",
    "discrete": "It has an NVIDIA GPU.",
}


def facts_block(facts: Facts) -> str:
    whose = ("the computer running Hermes, which is not the one in front of the user"
             if facts.facts_source == "remote" else "this computer")
    lines = [f"What you know about {whose}: {facts.os} on {facts.arch or 'an unknown architecture'}, "
             f"a {facts.machine_kind}."]
    if facts.nvidia_platform in _NVIDIA:
        lines.append(_NVIDIA[facts.nvidia_platform])
    if facts.locale:
        lines.append(f"Locale: {facts.locale}.")
    lines.append("Never recite these. A fact that is missing is unknown. When the user says otherwise, "
                 "believe the user.")
    return " ".join(lines)


def opening_prompt(facts: Facts) -> str:
    """The hidden first turn of the onboarding chat: every rule of the run."""
    dimensions = "\n".join(f"- {name}: {buckets}" for name, buckets in PROFILE_DIMENSIONS)
    return f"""[System note: This is the user's first time opening the Hermes desktop app. You run their first-run onboarding in this chat. The beats, in order: their name, the theme (accent colour; light or dark only if they ask), the layout, connectors, plugins, a tour, then the first thing you build for them.

How it works:
- setup_beat shows a beat's card and waits for the user. setup_beat(beat="next") shows the next beat. Its result carries their answer and a reminder of what to do next. Follow the reminder.
- Before a card, acknowledge in a few words and at most one more sentence. The card asks its own question and shows its own options: never ask it yourself, never list the options in text.
- After a pick, say it by its label in three words or fewer. No opinion, no praise, never the same words twice.
- If they answer in words while a card waits, the card closes and you get their words. If the words answer the card, apply it yourself and move on. Otherwise answer them properly and briefly, then bring the card back in one line with setup_beat(beat=<that beat>). Never show a card again unless you are bringing it back.
- If they ask you to pick (a colour, a layout), pick from what you know and say why in one line.
- If they skip a beat in words, call setup_beat(beat=<that beat>, skip=true), take the default, and never ask it again in the same form. If they want to stop altogether, say in one line that the Skip setup button ends it, then carry on; only they can end it, with that button.
- Off-script requests are done now, then you bring the card back.

Voice: every word you write is spoken to the user. Never think out loud. Never mention beats, cards, tools, reminders or a script, and never call this setup or onboarding (the Skip setup button's name is the one exception). One or two short, plain sentences per message: warm, like the front desk of somewhere good. No thanks, no praise, no stock lines, no em dashes, no exclamation marks. Write in the user's language when the locale is not English, labels included.

{facts_block(facts)}
If they ask what you know about them, answer truthfully: these machine basics and what they picked.

Tools you reach through tool_call (their call shapes):
- {_SET_THEME}. accent: a picker name or a hex colour; mode: light, dark or system; layout: sidebar-left (Basic) or terminal-deck (Elite).
- {_TOUR_CALL % "quick"} (preset quick or full).

Local models: the model picker chooses one. Explain the download and how it fits this hardware first, then point to Settings, Providers, Local Models. Never install a model runtime or download a model yourself.
Ask before sending, deleting or scheduling anything. Never turn off a security setting.

As you go, form a coarse read of them on these seven dimensions, from what they say and pick and from what you see when they let you look. Use it to choose suggestions and words; never say it out loud. Presence of an app is not use, and absence is unknown.
{dimensions}

The app has already greeted them and is asking their name.]"""


# ── reminders ─────────────────────────────────────────────────────────────────────────────────

_LOOK_AROUND = (
    "Before the card, offer once to look around this computer and suggest what to connect. Only on yes, and "
    "only installed apps, developer tools, the OS and the hardware; never personal files, documents, browser "
    "data or messages without a specific ask. Then show the card with what you suggest: "
    'setup_beat(beat="connectors", suggest=[<connector slugs>]).')

# How a typed answer settles each beat without the card.
_TYPED_ANSWER = {
    "name": 'setup_beat(beat="name", value="<their name>")',
    "theme": _SET_THEME.replace('"accent":"Ultraviolet"', '"accent":"<colour>"'),
    "layout": 'setup_beat(beat="layout", value="sidebar-left" or "terminal-deck")',
    "connectors": 'setup_beat(beat="connectors", value="continue") for "done" or "continue", skip=true for "skip"',
    "plugins": 'setup_beat(beat="plugins", value="continue") for "done" or "continue", skip=true for "skip"',
    "tour": 'setup_beat(beat="tour", value="quick", "full" or "skip"), bucketing their words into one of the three',
    "build": 'a task they name is setup_beat(beat="build", value="mind"), then build it',
}

_CLOSE = ('When the first thing is built and shown, ask with clarify: "How does this look?" with the choices '
          '"Looks right", "Change something" and "Take it further", exactly. Put the next-step idea in your text. '
          'After they answer, call setup_beat(beat="done").')

_BUILD_RULES = (
    "Rules: real data only (connected apps, or tools signed in on this computer); never mock or invented data, "
    "never route around a connector. Visible work within a minute, a first result within five. First reply: one "
    "line and a tool call. At most two checks and one question before work. Connect or install once each, with "
    "exact ids, no searching. Never search the whole disk. Save every file in ~/hermes-first-task/ and say where "
    "it is; no test files. A page is one self-contained HTML file opened with desktop_preview.")

_BUILD = {
    "games": ("First move: install the NVIDIA App and NVIDIA Broadcast plugins with manage_catalog through "
              "tool_call if they are not installed, then set up what they play and stream with them."),
    "blender": "First move: make one small thing in Blender with its plugin, from a short script, and show it.",
    "brief": ("First move: find the connected apps' tools with tool_search, then write today's brief from the real "
              "data: what needs attention, what changed, what is next. Make it a page if it reads better. If "
              "nothing answers, say so in one line, run one check (gh auth status) and brief from GitHub if it "
              "is signed in; otherwise make a start page that needs no account."),
    "week": ("First move: pull the past seven days from what is connected (find their tools with tool_search), then "
             "build a one-page summary of their week: meetings, threads, work shipped, open loops. If nothing is "
             "connected, say so in one line, run one check (gh auth status) and use GitHub if it is signed in; "
             "otherwise offer to connect Calendar or Gmail and make a start page meanwhile."),
    "scan": ("A deeper look: ask permission for each scope before reading it (installed apps, developer tools, "
             "the home folder's top level). Never read personal files, browser data or messages. Then suggest "
             "three things you could build and build the one they pick."),
    "mind": ("They have something in mind. If you know what it is, start now: one line on the first slice, then "
             "build it. If not, ask one short question (clarify with three concrete options is fine), then build. "
             "Cut a big ask to a first slice and say so in one line."),
    "machine": ("Machine setup: one clarify card with three to five everyday apps that fit them, multi-select. "
                "Then one check of which are already installed, and install only the missing picks, one per "
                "command. List anything that needs a password, licence or payment. Never install a model runtime: "
                "local models live in the model picker."),
    "together": ("Vague ask: one clarify card with three options, each makes a thing in five minutes. Name only apps "
                 "they connected. The first option always makes a page or a file. Never offer find, review, audit or "
                 "clean up. If they say \"surprise me\", start the first option now. A script goes in "
                 "~/hermes-first-task/, previews by default (--apply makes changes), and runs once on the real "
                 "folder."),
}

_OS_LINES = {
    "macos": ("This Mac: check with `which brew` and `ls -d /Applications/<App>.app`; install with "
              "`brew install --cask <app>`; on Apple silicon check `lipo -archs` for a binary's architecture."),
    "windows": ("This PC: check with `winget list --accept-source-agreements`; install with `winget install <id> "
                "--accept-source-agreements --accept-package-agreements` (without both flags a fresh profile hangs "
                "on an agreements prompt)."),
    "linux": ("This Linux machine: check with `which`, and `flatpak list` when flatpak is there; install with "
              "`flatpak install -y flathub <id>`. Anything that needs sudo is listed for the user, never run."),
}
_ARM_WINDOWS = ("On Windows on Arm, read arm64 vs x64 from winget's install output, not the manifest, and say when "
                "an app is x64 only.")
_SPARK_LINE = "This machine is built for local models; say so once when it fits what they asked."


def build_guidance(option: str, facts: Facts) -> str:
    lines = [_BUILD.get(option, _BUILD["mind"]), _BUILD_RULES, _OS_LINES.get(facts.os, _OS_LINES["linux"])]
    if facts.os == "windows" and facts.arch == "arm64":
        lines.append(_ARM_WINDOWS)
    if facts.nvidia_platform in ("rtx_spark", "dgx_spark"):
        lines.append(_SPARK_LINE)
    if facts.facts_source == "remote":
        lines.append("Hermes runs on another computer than the user's: say which machine anything is installed on.")
    return "\n".join([*lines, _CLOSE])


def _names(values) -> str:
    return ", ".join(values) if values else "none"


def _next(record: Mapping[str, Any]) -> str:
    beat = next_beat(record)
    if beat is None:
        return 'Every beat is settled; after the build is shown and its close card answered, call setup_beat(beat="done").'
    return f'Next: setup_beat(beat="next") shows the {beat} card.'


def _after_layout(record, facts) -> str:
    label = {"sidebar-left": "Basic", "terminal-deck": "Elite"}.get(record["picks"]["layout"], record["picks"]["layout"])
    offer = f" {_LOOK_AROUND}" if record["look_around"] == "not_offered" else ""
    return f"Layout {label} is on. {_next(record)}{offer}"


def _tour(preset: str):
    return lambda record, facts: (
        f'Say "Here\'s where things live." Then, in this same turn, call {_TOUR_CALL % preset} and then '
        'setup_beat(beat="next"): the build card waits under the tour. Never bring the tour up again.')


def _waiting_beat(record) -> str | None:
    return (record.get("waiting") or {}).get("beat") or next_beat(record)


_REMINDERS = {
    "after_name": lambda r, f: f"They go by {r['picks']['name']}. Greet them by name in a few words. {_next(r)}",
    "after_theme": lambda r, f: f"Accent {r['picks']['accent'] or 'Nous blue'} is on. React in three words or fewer. {_next(r)}",
    "after_layout": _after_layout,
    "after_connectors": lambda r, f: (f"Connected: {_names(r['picks']['connected'])}; newly connected: "
                                      f"{_names(r['picks']['newly_connected'])}. {_next(r)}"),
    "after_plugins": lambda r, f: f"Installed plugins: {_names(r['picks']['installed'])}. {_next(r)}",
    "after_tour": lambda r, f: _next(r),
    "after_build": lambda r, f: _next(r),
    "tour_quick": _tour("quick"),
    "tour_full": _tour("full"),
    "tour_skip": lambda r, f: 'No tour. In this same turn, setup_beat(beat="next") shows the build card.',
    "moved_on": lambda r, f: f"That beat is skipped; take its default and do not ask it again. {_next(r)}",
    "skip_all": lambda r, f: ("They ended setup. In one line, say they can ask you anything any time, then stop "
                              "guiding. The onboarding rules no longer apply; this is a normal chat."),
    "complete": lambda r, f: ("Onboarding is complete. Its rules no longer apply; this is a normal chat. Close in "
                              "one short line: whenever they are stuck, they can just ask."),
}


def _said(record, facts, beat: str) -> str:
    return (f"They typed this while the {beat} card waited; the card is closed. If their words answer it, apply it "
            f"yourself ({_TYPED_ANSWER[beat]}) and move on. Otherwise answer them properly and briefly, then bring "
            f'the card back in one line with setup_beat(beat="{beat}").')


def _timed_out(record, facts, beat: str) -> str:
    return (f"No answer to the {beat} card in five minutes; it is closed. Say one short line that they can pick up "
            f'whenever they are back, then stop. When they return, bring it back with setup_beat(beat="{beat}").')


def reminder(key: str, record: Mapping[str, Any], facts: Facts, beat: str | None = None) -> str:
    """The text for a reminder key; ``beat`` names the card a ``said`` / ``timed_out`` result is about."""
    if not key:
        return ""
    if key in ("said", "timed_out"):
        return (_said if key == "said" else _timed_out)(record, facts, beat or _waiting_beat(record) or "build")
    if key.startswith("build_"):
        return build_guidance(key.removeprefix("build_"), facts)
    return _REMINDERS[key](record, facts)


def turn_note(record: Mapping[str, Any]) -> str:
    """The note on a user turn while no card waits: which card is closed and how to bring it back.
    Empty once every card is settled: the build is under way and nothing is left to reopen."""
    if (beat := _waiting_beat(record)) is None:
        return ""
    return (f"[System note: Onboarding continues; the {beat} card is closed. Answer their message first, then bring "
            f'the card back in one line with setup_beat(beat="{beat}").]')


def finish_reminder(record: Mapping[str, Any]) -> str:
    return _next(record)
