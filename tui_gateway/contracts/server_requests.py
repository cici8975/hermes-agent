"""Server→client requests: the backend asks the renderer a question (``server_requests.send``).

Every entry is one request method: the ``params`` the frame carries (``session_id`` is added by
the transport and declared on the shared base) and the ``result`` the client answers with. The
``request.cancel`` event that withdraws an open request lives here too.
"""

from __future__ import annotations

from pydantic import Field

from tools.tour_presets import TourPreset

from .base import JsonValue, Params, Payload, Result, WireEnum
from .registry import event, server_request


class ServerRequestParams(Params):
    """Every request frame's params start with the session the question belongs to."""

    session_id: str


class ValueResult(Result):
    """The answer to any one-string prompt (sudo, secret, vault prompts, desktop bridges):
    ``''`` means skipped / declined."""

    value: str


# ── clarify ───────────────────────────────────────────────────────────────────────────────────


class ClarifyQuestion(Params):
    qid: str
    question: str
    choices: list[str] | None = None
    multi_select: bool = False


class ClarifyRequestParams(ServerRequestParams):
    """``answers`` rides only on a reconnect replay (locks the server already accepted; null = skipped)."""

    questions: list[ClarifyQuestion]
    answers: dict[str, str | None] | None = None


class ClarifyResult(Result):
    """``{answers}`` for the whole set (early locks go through the ``clarify.lock`` RPC); a response
    without ``answers`` is cancel-all."""

    answers: dict[str, str | None] | None = None


server_request("clarify", params=ClarifyRequestParams, result=ClarifyResult,
               doc="The clarify tool: ask the user 1-5 questions.")


class SetupChooseKind(WireEnum):
    question = "question"
    accent = "accent"
    theme = "theme"
    layout = "layout"
    connectors = "connectors"
    plugins = "plugins"
    tour = "tour"
    fork = "fork"
    machine_use = "machine_use"


class SetupChooseOption(Params):
    id: str
    label: str
    detail: str | None = None


class SetupChooseRequestParams(ServerRequestParams):
    kind: SetupChooseKind
    question: str
    options: list[SetupChooseOption] | None = None
    multi_select: bool = False
    # Row ids the card starts with picked: the plugins the setup facts found (Blender).
    preselected: list[str] | None = None


class SetupChooseResult(Result):
    picked: str | list[str] | None = None
    # The name the card showed for each picked row (one per id in ``picked``); the model says it, not the id.
    label: str | list[str] | None = None
    # Composer text that named no row of the card: the user's words, never a pick.
    said: str | None = None


server_request("setup_choose", params=SetupChooseRequestParams, result=SetupChooseResult)


# ── setup_beat (first-run onboarding) ─────────────────────────────────────────────────────────


class SetupBeat(WireEnum):
    name = "name"
    theme = "theme"
    layout = "layout"
    connectors = "connectors"
    plugins = "plugins"
    tour = "tour"
    build = "build"


class SetupBeatRequestParams(ServerRequestParams):
    """``card`` is the beat's data (``agent/onboarding_flow.py::BEATS``): name ``{suggested?}`` (the OS
    account's name, card-only), theme ``{picker}``, layout and tour ``{options}``, connectors
    ``{suggested}`` (slugs), plugins ``{plugins}`` (catalog names), build ``{options}``."""

    beat: SetupBeat
    question: str | None = None
    card: dict[str, JsonValue]


class SetupBeatResult(Result):
    """``answer`` holds the beat's picks (name ``{name}``, theme ``{accent, mode?}``, layout ``{layout}``,
    connectors ``{connected, newly_connected}``, plugins ``{installed}``, tour ``{tour}``, build
    ``{build}``); ``said`` is composer text typed while the card waited. A response with neither, or
    none within 300 s, closes the card unanswered."""

    answer: dict[str, JsonValue] | None = None
    said: str | None = None


server_request("setup_beat", params=SetupBeatRequestParams, result=SetupBeatResult,
               doc="The onboarding chat's card for one beat; blocks setup_beat until answered (300 s).")


# ── approval ──────────────────────────────────────────────────────────────────────────────────


class ApprovalChoice(WireEnum):
    once = "once"
    session = "session"
    always = "always"
    deny = "deny"


class ApprovalRequestParams(ServerRequestParams):
    """``tui_gateway/server.py::_approval_request_payload`` — the command is redacted server-side."""

    request_id: str
    command: str = ""
    description: str = ""
    choices: list[ApprovalChoice] = Field(default_factory=list)
    allow_permanent: bool | None = None
    allow_session: bool | None = None
    smart_denied: bool | None = None
    tool_name: str | None = None
    session_id_hint: str | None = Field(default=None, alias="gateway_session_id")
    # The approval queue entry carries tool-specific context the card may render; the closed set
    # of keys is owned by tools/approval.py, so it stays open here.
    model_config = Params.model_config | {"extra": "allow"}


class ApprovalResult(Result):
    choice: ApprovalChoice
    all: bool | None = None


server_request("approval", params=ApprovalRequestParams, result=ApprovalResult,
               doc="A dangerous command awaits the user's decision.")


# ── one-string prompts ────────────────────────────────────────────────────────────────────────


class EmptyRequestParams(ServerRequestParams):
    pass


class SudoRequestParams(ServerRequestParams):
    """Original command, redacted server-side before any password-injection rewrite."""

    command: str = ""


server_request("sudo", params=SudoRequestParams, result=ValueResult,
               doc="Masked sudo password for the terminal tool.")


class SecretRequestParams(ServerRequestParams):
    env_var: str
    prompt: str
    metadata: dict[str, JsonValue] | None = None


server_request("secret", params=SecretRequestParams, result=ValueResult,
               doc="Masked value for a named env var (skills / setup flows).")


class VaultUnlockRequestParams(ServerRequestParams):
    backend: str
    display_name: str


server_request("vault.unlock_prompt", params=VaultUnlockRequestParams, result=ValueResult,
               doc="Master password to unlock an external password manager for this session.")


class VaultSaveLoginRequestParams(ServerRequestParams):
    origin: str
    site: str


server_request("vault.save_login", params=VaultSaveLoginRequestParams, result=ValueResult,
               doc="Save a login for a site the agent is about to fill; the answer is JSON {identifier, password}.")


class VaultCodeRequestParams(ServerRequestParams):
    site: str | None = None
    hint: str | None = None


server_request("vault.code", params=VaultCodeRequestParams, result=ValueResult,
               doc="A one-time / 2FA code the user reads from their device.")


# ── desktop GUI bridges ───────────────────────────────────────────────────────────────────────


class ReadRangeRequestParams(ServerRequestParams):
    start: int | None = None
    count: int | None = None


server_request("terminal.read", params=ReadRangeRequestParams, result=ValueResult,
               doc="Read the visible in-app terminal buffer (JSON text answer).")
server_request("preview.read", params=ReadRangeRequestParams, result=ValueResult,
               doc="Read the in-app browser preview's text (JSON text answer).")
server_request("window.read", params=EmptyRequestParams, result=ValueResult,
               doc="Enumerate the native window below the app (JSON text answer).")


class PreviewActRequestParams(ServerRequestParams):
    """``tools/drive_preview_tool.py`` and ``tools/annotate_preview_tool.py`` field sets."""

    action: str
    ref: str | None = None
    selector: str | None = None
    text: str | None = None
    key: str | None = None
    submit: bool | None = None
    full: bool | None = None
    to: str | None = None
    amount: int | None = None
    max: int | None = None
    allow_shortcut: bool | None = None


server_request("preview.act", params=PreviewActRequestParams, result=ValueResult,
               doc="Click / type / scroll / annotate inside the in-app browser preview.")


class TourStep(Params):
    selector: str | None = None
    title: str | None = None
    text: str | None = None
    side: str | None = None
    model_config = Params.model_config | {"extra": "allow"}


class TourRequestParams(ServerRequestParams):
    """``tools/tour_tool.py`` field set."""

    action: str
    surface: str | None = None
    selector: str | None = None
    title: str | None = None
    text: str | None = None
    side: str | None = None
    steps: list[TourStep] | None = None
    step_index: int | None = None
    preset: TourPreset | None = None


server_request("tour", params=TourRequestParams, result=ValueResult,
               doc="Drive a guided tour highlight in the desktop renderer.")


class ThemeMode(WireEnum):
    light = "light"
    dark = "dark"
    system = "system"


class ThemePicker(WireEnum):
    accent = "accent"
    layout = "layout"


class ThemeApplyRequestParams(ServerRequestParams):
    """``tools/set_theme_tool.py`` values; accent is a swatch id, ``theme`` or ``#rrggbb``."""

    accent: str | None = None
    mode: ThemeMode | None = None
    layout: str | None = None


class ThemePickRequestParams(ServerRequestParams):
    picker: ThemePicker


class ThemeValues(Params):
    """What the renderer applied. ``accent`` is a swatch id, ``custom:#rrggbb``, or null for the theme's own."""

    accent: str | None = None
    mode: ThemeMode | None = None
    layout: str | None = None


class ThemePickResult(Result):
    """``picked`` once the user chose (already applied); ``cancelled`` when the card was dismissed. A response
    with neither is a cancel."""

    picked: ThemeValues | None = None
    said: str | None = None
    cancelled: bool | None = None


server_request("theme.apply", params=ThemeApplyRequestParams, result=ValueResult,
               doc="Apply set_theme values in the window showing the session (JSON text answer).")
server_request("theme.pick", params=ThemePickRequestParams, result=ThemePickResult,
               doc="Show an accent or layout picker card in the chat and wait for the pick.")


# ── withdrawal ────────────────────────────────────────────────────────────────────────────────


class RequestCancelReason(WireEnum):
    timeout = "timeout"
    interrupted = "interrupted"
    shutdown = "shutdown"
    resolved = "resolved"
    session_closed = "session_closed"


class RequestCancelPayload(Payload):
    id: str
    method: str
    reason: str  # a RequestCancelReason value; callers in tools/approval may pass their own wording


event("request.cancel", RequestCancelPayload,
      doc="The backend withdrew an open server→client request; clear the matching card only.")
