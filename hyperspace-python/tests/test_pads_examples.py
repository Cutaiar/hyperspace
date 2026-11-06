"""Plan 42's example patches (docs/plans/assets/42-controllers/patches/)
are patches this build spawns: the touchpad's and the motion sensors'
rows are rig rows like a hand's.

Every patch in the folder is checked against the real app — the shape
(`patches.check`), the pad lanes it reads (each one `pads/gesture.py` or
the pad publishes), each row's target and each value (a param the app's
own registry has, with the patch's envelope and LFO voices declared) —
and so are the session's rows beside it (session-rows/<patch>.json): the
sink rows that drive the pad back, which a patch may not carry (a sink is
the session's), and the pad-button rows a patch may not hold. Each sink
row names a real channel (`devices.SINKS`) and a param the patch drives,
and reads through `routing.sink_values` into `devices.pad_effects`.

The browser lab (prototypes/edge-lab/index.html) plays ideas 8–13 from a
copy of these files and of the app's ranges (its ``#labPatches`` island):
the copy is held equal to both here, so the lab's demo and its *copy
route* are the patch that ships."""

import json
import math
import re
from pathlib import Path

import pytest
from conftest import boot_home

from hyperspace import devices, envelope, gamepad, patches
from hyperspace import modifiers as modmod
from hyperspace.pads import gesture
from hyperspace.params import Kind
from hyperspace.routing import MOD_OPS, OPS, Binding, Bindings, sink_refusal, sink_values

ASSETS = Path(__file__).resolve().parents[1] / "docs" / "plans" / "assets" / "42-controllers"
HERE = ASSETS / "patches"
ROWS = ASSETS / "session-rows"
LAB_PAGE = Path(__file__).resolve().parents[2] / "prototypes" / "edge-lab" / "index.html"
NAMES = sorted(p.stem for p in HERE.glob("*.json"))
# the plan's two (ideas 4 and 5) and the lab's six (ideas 8–13): a file
# gone from the folder fails here rather than going unchecked
EXPECTED = {"touch-burst", "shake-hit", "grab-tilt", "spin-spin", "snow-globe",
            "trigger-detent", "wind-up", "thumb-roll"}
ROLE = "edge"            # the role plan 42's example config gives the Edge
PAD_SCHEMES = {"touch": set(gesture.TOUCH_LANES), "motion": set(gesture.MOTION_LANES),
               "axis": set(gamepad.AXES) | set(gamepad.DIAL_LANES)}


def doc_of(name: str) -> dict:
    return json.loads((HERE / f"{name}.json").read_text())


def rows_of(name: str) -> list[dict]:
    path = ROWS / f"{name}.json"
    return json.loads(path.read_text())["rows"] if path.is_file() else []


@pytest.fixture(scope="module")
def reg(tmp_path_factory):
    """The app's registry as a fresh home boots it (conftest.boot_home: the
    view, the effects, the LFOs 1–4, the clock), with the envelope bank
    and an envelope 6 declared — every id a patch's voice spawns under."""
    rig = boot_home(tmp_path_factory.mktemp("home"), corpus=False)
    envs = envelope.Envelopes()
    envelope.register(rig.reg, envs)
    envs.add(6)
    return rig.reg


def param(reg, pid: str, doc: dict):
    """A row's target as the app would hold it: one of the patch's own
    modifier knobs by its kind's spec (`mod.2.mul`; the registry declares
    them at spawn), anything else the registry's."""
    if pid.startswith(modmod.PREFIX):
        mid, _, key = pid.rpartition(".")
        kind = next((m["kind"] for m in doc["modifiers"] if m.get("id") == mid), None)
        return modmod.spec(kind, key) if kind else None
    return reg.get(pid)


def pad_lanes(doc: dict) -> list[str]:
    """Every pad lane the patch reads: its rows' sources and gates, its
    modifiers' inputs."""
    out = [r["source"] for r in doc["routes"]] + [r["when"] for r in doc["routes"] if "when" in r]
    for m in doc["modifiers"]:
        ins = m.get("in") or []
        out += [ins] if isinstance(ins, str) else [a for a in ins if a]
    return [a for a in out if a.partition(":")[0] in PAD_SCHEMES]


def test_the_folder_holds_the_plan_and_lab_patches():
    assert EXPECTED <= set(NAMES)
    # a session-rows file is a patch's, by its stem and its own word
    for path in ROWS.glob("*.json"):
        assert path.stem in NAMES, f"{path.name}: no patches/{path.name}"
        assert json.loads(path.read_text())["patch"] == path.stem


@pytest.mark.parametrize("name", NAMES)
def test_the_example_patches_check_and_read(name):
    doc = doc_of(name)
    assert patches.check(doc) == []
    p = patches.read(doc)
    assert p is not None
    assert all(r["op"] in MOD_OPS for r in doc["routes"]), "a patch route is a performer"
    lanes = pad_lanes(doc)
    assert lanes, f"{name} reads nothing of the pad"
    for a in lanes:
        scheme, _, lane = a.partition(":")
        assert lane in PAD_SCHEMES[scheme], f"{a}: the pad publishes no such lane"


@pytest.mark.parametrize("name", NAMES)
def test_every_target_and_value_is_a_param_the_app_has(name, reg):
    doc = doc_of(name)
    for r in doc["routes"]:
        p = param(reg, r["target"], doc)
        assert p is not None, f"route {r['source']} → {r['target']}: no such param"
        if r["op"] == "position" and isinstance(p.kind, Kind):
            assert p.kind is not Kind.TRIGGER, f"{r['target']}: position on a trigger"
    for pid, v in doc["values"].items():
        p = reg.get(pid)
        assert p is not None, f"value {pid}: no such param"
        if p.kind is Kind.CONTINUOUS:
            # an envelope's hold: the knob's bottom (1 ms) is 0 (envelope.py)
            lo = 0.0 if pid.startswith("env.") and pid.endswith(".hold") else min(p.lo, p.hi)
            assert lo <= v <= max(p.lo, p.hi), f"{pid} = {v} outside {p.lo}…{p.hi}"
        elif p.kind is Kind.ENUM:
            assert 0 <= v < len(p.names), f"{pid} = {v}: no such choice"
        elif p.kind is Kind.TOGGLE:
            assert isinstance(v, bool), f"{pid}: a toggle is true or false"


@pytest.mark.parametrize("name", [n for n in NAMES if (ROWS / f"{n}.json").is_file()])
def test_the_meta_rows_drive_the_pad_back(name, reg):
    """Each sink row names a real channel and a param the patch drives (a
    route's target or one of its own), the param continuous (a trigger
    reads 0 out); each pad row a button the pad has, onto a param of the
    patch's, with the op Learn pad gives it. Read out, the sink rows fill
    exactly their channels and make the pad's effects."""
    doc, rows = doc_of(name), rows_of(name)
    assert rows
    members = patches.read(doc).members
    driven = {r["target"] for r in doc["routes"]}
    sinks = []
    for d in rows:
        b = Binding.from_json(d)
        assert b.op in OPS
        if b.is_sink:
            assert sink_refusal(b) is None, sink_refusal(b)
            role, ch = b.sink
            assert role == ROLE and 0 <= ch < len(devices.SINKS), f"{b.target}: no such channel"
            scheme, _, pid = b.source.partition(":")
            assert scheme == "param"
            p = reg.get(pid)
            assert p is not None and p.kind is Kind.CONTINUOUS, f"{b.source}: no continuous param"
            assert pid in driven or members.owns(pid), f"{pid}: the patch does not move it"
            sinks.append(b)
        else:
            scheme, _, button = b.source.partition(":")
            assert scheme == "pad" and button in gamepad.ALL_BUTTONS, f"{b.source}: no such button"
            p = reg.get(b.target)
            assert p is not None and members.owns(b.target), f"{b.target}: not the patch's"
            want = {Kind.TRIGGER: "fire", Kind.TOGGLE: "toggle"}.get(p.kind)
            assert b.op == want, f"{b.source} → {b.target}: Learn pad gives {want}"
    assert sinks, f"{name}: no row drives the pad back"
    table = Bindings(sinks)
    vals = sink_values(table.sinks(ROLE), reg)
    assert sorted(vals) == sorted({b.sink[1] for b in sinks})
    assert all(math.isfinite(v) and 0.0 <= v <= 1.0 for v in vals.values())
    fx = devices.pad_effects(vals, ((0, 0, 255), 1))
    assert fx is not None


def test_the_detents_wall_is_the_radial_split():
    """Idea 11's maths, as the lab's self-test runs it: two clamped scales
    make a step about 72 % of L2's travel, nothing below it, all of it past."""
    doc = doc_of("trigger-detent")
    m1, m2 = (modmod.Modifier.from_json(m) for m in doc["modifiers"])

    def wall(lt: float) -> float:
        st = modmod.ModState()
        a = modmod.step(m1, (lt,), st, 0.016)
        return modmod.step(m2, (a,), modmod.ModState(), 0.016)
    assert wall(0.0) == 0.0 and wall(0.69) == 0.0
    assert 0.0 < wall(0.725) < 1.0
    assert wall(0.76) == 1.0 and wall(1.0) == 1.0


def test_spin_spin_reads_the_spin_either_way():
    """Idea 9: |spin| from the signed lane, so a turn either way smears."""
    doc = doc_of("spin-spin")
    m = {d["id"]: modmod.Modifier.from_json(d) for d in doc["modifiers"]}

    def smear(u: float) -> float:
        a = modmod.step(m["mod.2"], (u,), modmod.ModState(), 0.016)
        b = modmod.step(m["mod.3"], (u,), modmod.ModState(), 0.016)
        return modmod.step(m["mod.4"], (a, b), modmod.ModState(), 0.016)
    assert smear(0.5) == 0.0
    assert smear(1.0) == smear(0.0) == 1.0
    assert abs(smear(0.75) - 0.5) < 1e-9 and abs(smear(0.25) - 0.5) < 1e-9


def test_the_lab_plays_the_patches_that_ship(reg):
    """The lab's island: each of its patches and session rows is the file's,
    word for word, every file with session rows is in it, and each range it
    runs a param on is the registry's (kind, ends, log, wrap, choices, the
    fresh home's base)."""
    if not LAB_PAGE.is_file():
        pytest.skip("no prototypes/edge-lab beside this checkout")
    found = re.search(r'<script type="application/json" id="labPatches">(.*?)</script>',
                      LAB_PAGE.read_text(), re.DOTALL)
    assert found, "the lab has no #labPatches island"
    lab = json.loads(found.group(1))
    words = "paste patches/{0}.json and session-rows/{0}.json into the lab's #labPatches"
    assert set(lab["patches"]) == {p.stem for p in ROWS.glob("*.json")}
    for name, doc in lab["patches"].items():
        assert doc == doc_of(name), words.format(name)
        assert lab["rows"][name] == rows_of(name), words.format(name)
    for pid, s in lab["params"].items():
        p = reg.get(pid)
        assert p is not None, f"the lab runs {pid}, which the app has not"
        want = {"k": p.kind.value, "lo": p.lo, "hi": p.hi,
                "base": None if p.kind is Kind.TRIGGER else p.base}
        if p.log:
            want["log"] = True
        if p.wrap:
            want["wrap"] = True
        if p.kind is Kind.ENUM:
            want["n"] = len(p.names)
        assert s == want, f"the lab's range for {pid}: {s} — the app's: {want}"
    for name, doc in lab["patches"].items():
        touched = {r["target"] for r in doc["routes"]} | {
            r["source"][len("param:"):] if r["op"] == "send" else r["target"]
            for r in lab["rows"][name]}
        missing = touched - set(lab["params"])
        assert not missing, f"{name}: the lab has no range for {missing}"
