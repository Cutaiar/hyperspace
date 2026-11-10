"""The projector's battery over ADB (hyperspace/projector.py): the parse of
`dumpsys battery`, the one ask, the watch's kept reading, the readout line."""

import ast
from pathlib import Path

from hyperspace import projector
from hyperspace.projector import Battery, Reading, Watch, alert, ask, detail, parse, words

DUMPSYS = """Current Battery Service state:
  AC powered: true
  USB powered: false
  Wireless powered: false
  Max charging current: 0
  Max charging voltage: 0
  Charge counter: 0
  status: 2
  health: 2
  present: true
  level: 85
  scale: 100
  voltage: 8123
  temperature: 312
  technology: Li-ion
  mWakefulness=Awake
"""


def test_parse_reads_the_state_of_charge():
    b = parse(DUMPSYS)
    assert b == Battery(percent=85, status="charging", plugged=("ac",), present=True,
                        temp_c=31.2, volts=8.123, wake="awake")
    assert b.charging


def test_parse_scales_level_over_scale_and_clamps():
    assert parse("  level: 50\n  scale: 200\n").percent == 25
    assert parse("  level: 120\n  scale: 100\n").percent == 100
    assert parse("  level: 7\n  scale: 0\n").percent == 7           # a scale of 0 is 100


def test_parse_without_a_level_is_none():
    assert parse("") is None
    assert parse("error: device offline\n") is None
    assert parse("  level: n/a\n") is None


def test_parse_says_discharging_and_a_missing_battery():
    b = parse("  status: 3\n  present: false\n  level: 100\n")
    assert b.status == "discharging" and not b.charging and not b.present and b.plugged == ()


def fake(answers):
    calls = []

    def run(argv, timeout):
        calls.append(argv)
        return answers[argv[1] if argv[1] == "connect" else "shell"]
    return run, calls


def test_ask_connects_then_reads_the_battery():
    run, calls = fake({"connect": (0, "connected to 10.0.0.9:5555\n"), "shell": (0, DUMPSYS)})
    b, err = ask("10.0.0.9:5555", "adb", run)
    assert err is None and b.percent == 85
    assert calls == [["adb", "connect", "10.0.0.9:5555"],
                     ["adb", "-s", "10.0.0.9:5555", "shell", projector.SHELL]]


def test_ask_says_why_it_failed():
    run, _ = fake({"connect": (1, "failed to connect to '10.0.0.9:5555': No route to host"),
                   "shell": (0, DUMPSYS)})
    assert ask("10.0.0.9:5555", "adb", run) == (None, "unreachable")
    run, _ = fake({"connect": (0, "already connected to 10.0.0.9:5555"),
                   "shell": (1, "error: device unauthorized.")})
    b, err = ask("10.0.0.9:5555", "adb", run)
    assert b is None and err.startswith("unauthorised")
    assert projector.run_adb(["/no/such/adb", "devices"], 1.0) == (127, "adb not found")


def test_the_watch_keeps_the_last_good_battery_through_a_failure():
    state = {"up": True}
    t = [100.0]

    def run(argv, timeout):
        if not state["up"]:
            return 1, "failed to connect"
        return (0, "connected to h:5555") if argv[1] == "connect" else (0, DUMPSYS)

    w = Watch("h", runner=run, adb="adb", clock=lambda: t[0])
    assert w.serial == "h:5555" and w.latest() == Reading()
    w.poll()
    assert w.latest().battery.percent == 85 and w.latest().at == 100.0
    state["up"] = False
    t[0] = 400.0
    r = w.poll()
    assert r.battery.percent == 85 and r.at == 100.0 and r.error == "unreachable"
    assert words(r, now=400.0) == "projector 85 % · charging · awake · 5 min ago · unreachable"


def test_the_watch_thread_starts_and_closes():
    run, _ = fake({"connect": (0, "connected to h:5555"), "shell": (0, DUMPSYS)})
    w = Watch("h:5555", every=60.0, runner=run, adb="adb").start()
    w.close()
    assert w.latest().battery.percent == 85


def test_words():
    assert words(Reading()) == "projector —"
    assert words(Reading(error="adb not found")) == "projector — · adb not found"
    on_mains = Reading(Battery(60, status="not charging", plugged=("ac",)), at=0.0)
    assert words(on_mains, now=1.0) == "projector 60 % · plugged in"
    assert words(Reading(Battery(40, status="discharging"), at=0.0), now=1.0) == "projector 40 %"


def test_parse_reads_asleep_and_no_wakefulness():
    assert parse("  level: 50\n  mWakefulness=Asleep\n").wake == "asleep"
    assert parse("  level: 50\n").wake is None


def test_the_header_speaks_only_when_it_matters():
    assert alert(Reading()) == ""                                       # never answered: the page says it
    assert alert(Reading(error="unreachable")) == ""
    fine = Battery(85, status="discharging", wake="awake")
    assert alert(Reading(fine, at=0.0)) == ""
    assert alert(Reading(Battery(14, status="discharging"), at=0.0)) == "projector 14 %"
    assert alert(Reading(Battery(14, status="charging"), at=0.0)) == ""
    assert alert(Reading(Battery(14, plugged=("ac",)), at=0.0)) == ""
    assert alert(Reading(Battery(14, present=False), at=0.0)) == ""   # a fake battery isn't low
    assert alert(Reading(Battery(90, wake="asleep"), at=0.0)) == "projector asleep"
    assert alert(Reading(fine, at=0.0, error="unauthorised: accept the prompt")) == "projector unauthorised"
    assert alert(Reading(fine, at=0.0, error="unreachable")) == "projector unreachable"


def test_the_hover_says_every_number():
    r = Reading(parse(DUMPSYS), at=10.0, error="unreachable")
    text = detail(r, "h:5555", now=40.0)
    assert "h:5555" in text and "battery 85 %, charging, plugged in: ac" in text
    assert "31.2 °C, 8.12 V, screen awake" in text and "read 30 s ago" in text
    assert "last ask: unreachable" in text
    assert "not asked yet" in detail(Reading(), "h:5555")


def test_the_app_opens_a_watch_only_with_a_host(monkeypatch):
    from hyperspace import app
    started = []
    monkeypatch.setattr(Watch, "start", lambda self: started.append(self) or self)
    assert app._open_projector({}) is None
    assert app._open_projector({"projector": {"host": "  "}}) is None
    w = app._open_projector({"projector": {"host": "10.0.0.9", "every": 60}})
    assert w.serial == "10.0.0.9:5555" and w.every == 60.0 and started == [w]
    assert app._open_projector({"projector": {"host": "10.0.0.9", "every": 0}}).every == projector.EVERY_S


def test_projector_is_a_leaf():
    """The standard library only: nothing from the package, no GL, no imgui."""
    tree = ast.parse(Path(projector.__file__).read_text())
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            assert not n.level, n.module
            mods = [n.module or ""]
        elif isinstance(n, ast.Import):
            mods = [a.name for a in n.names]
        else:
            continue
        for mod in mods:
            assert mod.split(".")[0] in {"__future__", "shutil", "subprocess", "threading",
                                         "time", "dataclasses", "typing"}, mod
