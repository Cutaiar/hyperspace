"""app.Awake: the Mac kept out of the screensaver while the app runs."""

from __future__ import annotations

import subprocess
import sys

import pytest

from hyperspace import app, config


class FakeProc:
    def __init__(self, args, **kw):
        self.args, self.kw = args, kw
        self.terminated = self.waited = False

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        self.waited = True
        return 0


def test_caffeinate_holds_display_and_idle_sleep_tied_to_our_pid():
    a = app.Awake(pid=4321, popen=FakeProc, which=lambda _: "/usr/bin/caffeinate",
                  platform="darwin")
    assert a.note == ""
    assert a.proc.args == ["/usr/bin/caffeinate", "-d", "-i", "-w", "4321"]
    proc = a.proc
    a.close()
    assert proc.terminated and proc.waited and a.proc is None
    a.close()                                   # a second close is nothing


def test_not_macos_or_no_caffeinate_is_a_note_never_a_raise():
    a = app.Awake(popen=FakeProc, which=lambda _: "/x", platform="linux")
    assert a.proc is None and "not macOS" in a.note
    a = app.Awake(popen=FakeProc, which=lambda _: None, platform="darwin")
    assert a.proc is None and "no caffeinate" in a.note

    def boom(*_a, **_k):
        raise OSError("denied")
    a = app.Awake(popen=boom, which=lambda _: "/x", platform="darwin")
    assert a.proc is None and "denied" in a.note
    a.close()


def test_keep_awake_is_on_by_default_and_the_config_can_turn_it_off(monkeypatch):
    made = []
    monkeypatch.setattr(app, "Awake", lambda: made.append(1) or type("A", (), {"note": ""})())
    assert app._open_awake({"output": {"keep_awake": False}}) is None
    assert made == []
    assert app._open_awake({"output": {}}) is not None
    assert app._open_awake({"output": {"keep_awake": True}}) is not None
    assert len(made) == 2


def test_a_keep_awake_that_is_not_a_switch_stays_on_with_a_note(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text('[output]\nkeep_awake = "no"\n')
    cfg = config.load(p)
    assert cfg["output"]["keep_awake"] is True
    assert any("keep_awake" in n for n in cfg["notes"])
    assert config.load(tmp_path / "none.toml")["output"]["keep_awake"] is True


@pytest.mark.skipif(sys.platform != "darwin", reason="caffeinate is macOS's")
def test_the_real_caffeinate_asserts_no_display_sleep_and_lets_go():
    def held() -> bool:
        out = subprocess.run(["pmset", "-g", "assertions"], capture_output=True,
                             text=True, check=False).stdout
        return any(f"pid {a.proc.pid}(caffeinate)" in line and "PreventUserIdleDisplaySleep"
                   in line for line in out.splitlines()) if a.proc else False
    a = app.Awake()
    try:
        assert a.proc is not None, a.note
        import time
        for _ in range(20):                     # caffeinate takes a moment to assert
            if held():
                break
            time.sleep(0.05)
        assert held()
    finally:
        proc = a.proc
        a.close()
    assert proc.poll() is not None
