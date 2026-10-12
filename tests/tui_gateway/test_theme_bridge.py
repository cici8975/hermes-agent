"""``set_theme`` picker bridge: the model can tell a pick, a dismissed card and an expired one apart.
See tui_gateway.server._theme_request."""

from types import SimpleNamespace

import pytest

from tui_gateway import server, server_requests


@pytest.mark.parametrize(("answer", "elapsed", "result"), [
    ({"picked": {"accent": "violet"}}, 4.0, {"success": True, "picked": {"accent": "violet"}}),
    ({"said": " make it pink "}, 4.0, {"said": "make it pink"}),
    ({"cancelled": True}, 4.0, {"cancelled": True}),
    (None, 4.0, {"cancelled": True}),
    (None, server._THEME_PICK_TIMEOUT_S, {"timed_out": True}),
])
def test_pick_outcomes(monkeypatch, answer, elapsed, result):
    clock = iter((0.0, elapsed))
    sent = []

    def fake_send(method, sid, params, *, timeout, **_kw):
        sent.append((method, sid, params, timeout))
        return answer

    monkeypatch.setattr(server_requests, "send", fake_send)
    monkeypatch.setattr(server, "time", SimpleNamespace(monotonic=lambda: next(clock)))
    monkeypatch.setitem(server._sessions, "s1", {})

    assert server._theme_request("s1", {"picker": "accent"}) == result
    assert sent == [("theme.pick", "s1", {"picker": "accent"}, server._THEME_PICK_TIMEOUT_S)]
