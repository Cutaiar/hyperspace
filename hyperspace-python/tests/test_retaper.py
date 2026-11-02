"""Wave 0 T1: coarse and fine control through tapers — the effects' `speed`
on a signed exponential taper, their `amount` params on a zero-safe log
taper, and every saved depth onto one measured along it, migrated in the
same change (`params.retaper_depths`, tools/retaper_routes.py).

Every tool test runs on a scratch library under tmp_path; the machine home
(the backup's place) is the conftest's tmp one."""

from __future__ import annotations

import importlib.util
import itertools
import json
import math
import sys
from pathlib import Path

import pytest

from hyperspace import fx, headless, preset, tapers
from hyperspace.fx import FxState, declare
from hyperspace.params import (
    DEPTH_TAPER,
    DEPTH_UNIT,
    UNITS,
    UNITS_KEY,
    Kind,
    Param,
    Registry,
    retaper_depths,
)
from hyperspace.routing import Binding

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "tests" / "corpus" / "presets"

# PR #304's amount-type params, the ones the `amount` flag now marks
AMOUNTS = {"fx.acid.bend", "fx.acid.twist", "fx.acid.breathe", "fx.deconverge.amount",
           "fx.deconverge.radial", "fx.displace.amount", "fx.doublevision.amount",
           "fx.fractals.amount", "fx.glimmer.amount", "fx.plasma.level",
           "fx.tripcolour.amount", "fx.warp.amount", "fx.wobble.amount", "fx.zoomblur.amount"}


def _tool():
    if "retaper_routes" in sys.modules:
        return sys.modules["retaper_routes"]
    spec = importlib.util.spec_from_file_location("retaper_routes",
                                                  ROOT / "tools" / "retaper_routes.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["retaper_routes"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def files():
    return FxState().files


@pytest.fixture(scope="module")
def reg():
    r = Registry()
    declare(r, FxState())
    return r


# ---------------------------------------------------------------- the tapers

@pytest.mark.parametrize("taper", [fx.T_SPEED, fx.amount_taper(2.0), fx.amount_taper(0.05),
                                   tapers.exp_signed(100, 160), tapers.exp_amount(3.1416, 8)],
                         ids=["speed", "amount 2", "amount 0.05", "signed 100/160", "amount π"])
def test_the_new_tapers_round_trip_on_every_detent(taper):
    """The law every taper keeps: unmap(map(p)) == p over the whole throw,
    and map is strictly increasing in a float position (a lane's)."""
    for p in range(taper.steps + 1):
        assert taper.unmap(taper.map(p)) == p, p
    ys = [taper.map(k / 4) for k in range(4 * taper.steps + 1)]
    assert all(b > a for a, b in itertools.pairwise(ys))


def test_the_speed_taper_is_signed_with_the_stop_in_the_middle():
    t = fx.T_SPEED
    assert t.steps == 2 * fx.SPEED_SIDE
    assert t.map(0) == -fx.SPEED_MAX and t.map(t.steps) == fx.SPEED_MAX
    assert t.map(fx.SPEED_SIDE) == 0.0 and t.unmap(0.0) == fx.SPEED_SIDE
    assert t.map(t.unity) == 1.0 and t.map(fx.SPEED_SIDE - fx.SPEED_UNITY) == -1.0
    # continuous through the stop: the ramp to the first step, no jump
    one = t.map(fx.SPEED_SIDE + 1)
    assert 0 < one < 0.01
    assert t.map(fx.SPEED_SIDE + 0.5) == pytest.approx(one / 2)
    assert t.map(fx.SPEED_SIDE - 0.5) == pytest.approx(-one / 2)
    # a tiny speed is not the stop (it lands one step out), a NaN is
    assert t.unmap(1e-6) == fx.SPEED_SIDE + 1 and t.unmap(-1e-6) == fx.SPEED_SIDE - 1
    assert t.unmap(math.nan) == fx.SPEED_SIDE


def test_the_amount_taper_is_off_at_zero_and_reaches_hi():
    t = fx.amount_taper(2.0)
    assert t.steps == fx.AMOUNT_OCTAVES * tapers.OCT
    assert t.map(0) == 0.0 and t.map(t.steps) == 2.0
    assert t.map(1) == pytest.approx(2.0 * 2 ** ((1 - t.steps) / tapers.OCT))
    assert t.map(0.5) == pytest.approx(t.map(1) / 2)       # the ramp
    assert t.unmap(0.0) == 0 and t.unmap(-1.0) == 0 and t.unmap(math.nan) == 0
    assert t.unmap(1e-9) == 1                              # on, however little
    assert t.unmap(t.map(100)) == 100 and t.map(100) == pytest.approx(2.0 / 32)
    assert fx.amount_taper(2.0) is t                       # one per hi


# ---------------------------------------------------------------- the params

def test_speed_and_the_amount_params_are_on_the_tapers_and_nothing_else_is(reg):
    """Exactly PR #304's amount-type params carry the flag; every effect's
    `speed` is on `T_SPEED`; `mix`, the log shape params and the rest keep
    their ranges."""
    amounts = {p.id for p in reg if p.taper is not None and p.taper is not fx.T_SPEED}
    assert amounts == AMOUNTS
    speeds = {p.id for p in reg if p.taper is fx.T_SPEED}
    assert speeds == {f"fx.{n}.speed" for n in FxState().specs}
    for p in reg:
        if p.id in amounts:
            assert (p.lo, p.steps) == (0.0, 200) and p.taper.map(p.steps) == p.hi
        elif p.id in speeds:
            assert (p.lo, p.hi, p.steps) == (-8.0, 8.0, 400)
    for pid in ("fx.warp.mix", "fx.warp.scale", "fx.warp.drift", "fx.kaleido.swirl",
                "fx.huecycle.paint", "fx.zoomblur.glow", "fx.mix"):
        assert reg[pid].taper is None, pid
    assert reg["fx.warp.scale"].log


def test_a_seven_bit_knob_reaches_a_twentieth_of_the_speed_and_the_amount(reg):
    """Hand check 420's maths: an APC knob (128 values through `set_norm`)
    lands 0.05× and 5 % of an amount's range within a step — on the old
    linear ranges 0.05× was 0.003 of the throw, under one MIDI value."""
    speed, amount = reg["fx.warp.speed"], reg["fx.warp.amount"]
    hits = [speed.base for k in range(128) if (speed.set_norm(k / 127) or True)
            and 0.045 <= speed.base <= 0.055]
    assert hits, "no knob value lands 0.05×"
    speed.set_norm(0.5)
    assert speed.base == 0.0 and speed.text() == "stop"
    speed.set_norm(1.0)
    assert speed.base == 8.0 and speed.text() == "+8.00×"
    speed.set_norm(0.0)
    assert speed.base == -8.0
    hits = [amount.base for k in range(128) if (amount.set_norm(k / 127) or True)
            and 0.09 <= amount.base <= 0.11]
    assert hits, "no knob value lands 5 % of warp amount"
    amount.set_norm(0.0)
    assert amount.base == 0.0 and amount.text() == "0"
    assert fx.fmt_speed(0.05) == "+0.050×" and fx.fmt_speed(-0.25) == "-0.25×"
    assert fx.fmt_amount(0.0016) == "0.0016" and fx.fmt_amount(16) == "16"


def test_an_amount_flag_wants_a_float_from_zero(reg):
    good = 'uniform float u_a; // @param 0 2 0.5 amount "A" t\nvec4 effect(vec2 uv) { return vec4(0); }'
    assert fx.parse("t", good).params[0].amount
    for bad in (good.replace("0 2 0.5 amount", "0.1 2 0.5 amount"),
                good.replace("0 2 0.5 amount", "0.5 2 1 log amount"),
                good.replace("amount", "wrap amount"),
                good.replace("uniform float", "uniform int")):
        with pytest.raises(fx.SpecError, match="amount"):
            fx.parse("t", bad)
    # the flag is part of the spec's signature: a file edited to add it re-declares
    a, b = fx.parse("t", good), fx.parse("t", good.replace(" amount", ""))
    assert a.signature() != b.signature()


# ---------------------------------------------------------------- the migration

def _linear(lo: float, hi: float, value: float) -> Param:
    box = {"v": value}
    return Param("old", "", Kind.CONTINUOUS, lambda: box["v"], lambda x: box.__setitem__("v", x),
                 lo=lo, hi=hi)


def _tapered(taper, lo: float, hi: float, value: float) -> Param:
    box = {"v": value}
    return Param("new", "", Kind.CONTINUOUS, lambda: box["v"], lambda x: box.__setitem__("v", x),
                 taper=taper, lo=lo, hi=hi)


def _reach(p: Param, offset: float) -> float:
    """What a performer's offset lands on `p`: modulate, apply, read."""
    p.modulate(offset)
    p.apply()
    v = float(p.value)
    p.apply()           # let go: the base comes back
    return v


@pytest.mark.parametrize("target, base, depth", [
    ("fx.warp.amount", 0.2, 0.3), ("fx.warp.amount", 0.9, 0.3), ("fx.warp.amount", 0.0, 0.5),
    ("fx.warp.amount", 1.5, -0.4), ("fx.acid.bend", 0.04, 0.6), ("fx.wobble.amount", 0.004, 0.5),
    ("fx.acid.speed", 4.0, 0.5), ("fx.acid.speed", 0.25, -0.3), ("fx.acid.speed", 0.0, 0.25),
    ("fx.acid.speed", -1.0, 0.8), ("fx.acid.2.bend", 0.1, 0.2),
])
def test_a_migrated_push_reaches_the_same_real_value_at_full_depth(files, target, base, depth):
    """A push row's real-unit reach at full push (u − rest = 1) about the
    row's base is the same before (linear) and after (the taper and the
    migrated depth); at rest both sit on the base."""
    lo, hi, _, taper = fx.retaper_of(target, files)
    doc = {"values": {target: base},
           "routes": [{"source": "hand:right.y", "target": target, "op": "push", "value": depth}]}
    out, moved = retaper_depths(doc, files)
    new = out["routes"][0].get("value", 1.0)
    old_p, new_p = _linear(lo, hi, base), _tapered(taper, lo, hi, base)
    assert _reach(new_p, new) == pytest.approx(_reach(old_p, depth), rel=1e-6, abs=1e-9)
    assert _reach(new_p, 0.0) == pytest.approx(base) and _reach(old_p, 0.0) == pytest.approx(base)
    assert out[UNITS_KEY][DEPTH_UNIT] == DEPTH_TAPER
    assert len(moved) == 1 and f"about {base:g}" in moved[0]


@pytest.mark.parametrize("target, depth", [
    ("fx.warp.amount", 1.0), ("fx.warp.amount", 0.6), ("fx.plasma.level", 0.25),
    ("fx.acid.speed", 1.0), ("fx.acid.speed", 0.75), ("fx.acid.speed", 0.5), ("fx.acid.speed", 2.0),
])
def test_a_migrated_position_lands_the_same_real_value_at_full_throw(files, target, depth):
    """A position row: the source at 1 lands the same real value before
    and after; a depth of 1 (the default, omitted) stays 1."""
    lo, hi, _, taper = fx.retaper_of(target, files)
    doc = {"values": {}, "routes": [{"source": "lfo:0", "target": target, "op": "position",
                                     "value": depth}]}
    out, _ = retaper_depths(doc, files)
    new = out["routes"][0].get("value", 1.0)
    old_p, new_p = _linear(lo, hi, lo), _tapered(taper, lo, hi, lo)
    want = old_p._value_of_norm(min(1.0, depth))
    assert new_p._value_of_norm(new) == pytest.approx(want, rel=1e-6, abs=1e-9)
    if depth == 1.0:
        assert new == 1.0


def test_the_conversion_reads_a_missing_value_as_one_and_a_missing_base_as_the_default(files):
    """`Binding.value` defaults to 1.0 and `to_json` omits it, so a row
    without one is a push of 1.0 (not 0); a preset that does not name the
    param pushes about the effect's default."""
    doc = {"values": {}, "routes": [
        {"source": "hand:right.y", "target": "fx.warp.amount", "op": "push"},
        {"source": "env:2", "target": "fx.warp.amount", "op": "position"}]}
    out, moved = retaper_depths(doc, files)
    push, pos = out["routes"]
    lo, hi, default, taper = fx.retaper_of("fx.warp.amount", files)
    old_p, new_p = _linear(lo, hi, default), _tapered(taper, lo, hi, default)
    assert _reach(new_p, push["value"]) == pytest.approx(_reach(old_p, 1.0))
    assert "value" not in pos and len(moved) == 1 and "about 0.2" in moved[0]


def test_only_rows_onto_retapered_params_move_and_a_macros_base_sub_moves_as_a_position(files):
    other = [{"source": "lane:0", "target": "rot.rate.XY", "op": "push", "value": 0.12},
             {"source": "hand:left.y", "target": "fx.warp.mix", "op": "position", "value": 0.7},
             {"source": "hand:left.z", "target": "fx.warp.scale", "op": "push", "value": 0.3},
             {"source": "cc@launch:0:7", "target": "fx.warp.amount", "op": "abs"},
             {"source": "hand:left.x", "target": "fx.warp.amount", "op": "push", "value": "x"},
             {"source": "hand:left.x", "target": "fx.nope.amount", "op": "push", "value": 0.5}]
    doc = {"values": {"fx.warp.amount": 0.2, "fx.warp.speed": 0.25},
           "routes": [*other, {"source": "pad:A", "target": "fx.warp.amount", "op": "set",
                               "value": 0.5}],
           "desk": [{"source": "cc:0:48", "target": "fx.warp.speed", "op": "abs"},
                    {"source": "note:0:53", "target": "fx.warp.speed", "op": "set",
                     "value": 0.75}],
           "macros": {"macro.1": {"label": "", "subs": [
               {"base": "fx.warp.amount", "from": 0.25, "to": 0.8},
               {"base": "fx.warp.mix", "from": 0.0, "to": 0.8},
               {"depth": {"source": "hand:right.y", "target": "fx.warp.amount"},
                "from": 0.0, "to": 1.0}]}}}
    out, moved = retaper_depths(doc, files)
    assert out["routes"][:6] == other
    lo, hi, _, taper = fx.retaper_of("fx.warp.amount", files)
    new_p = _tapered(taper, lo, hi, 0.2)
    assert new_p._value_of_norm(out["routes"][6]["value"]) == pytest.approx(0.5 * hi)
    slo, shi, _, st = fx.retaper_of("fx.warp.speed", files)
    assert out["desk"][0] == doc["desk"][0]
    speed = _tapered(st, slo, shi, 0.25)
    assert speed._value_of_norm(out["desk"][1]["value"]) == pytest.approx(slo + 0.75 * (shi - slo))
    sub, mix_sub, depth_sub = out["macros"]["macro.1"]["subs"]
    assert new_p._value_of_norm(sub["from"]) == pytest.approx(0.25 * hi)
    assert new_p._value_of_norm(sub["to"]) == pytest.approx(0.8 * hi)
    assert mix_sub == doc["macros"]["macro.1"]["subs"][1]
    assert depth_sub == doc["macros"]["macro.1"]["subs"][2]
    assert len(moved) == 4
    assert doc["routes"][6]["value"] == 0.5          # the document given is not written on


def test_a_marked_document_is_left_alone_and_the_marker_is_what_a_save_writes(files):
    doc = {"values": {}, "units": {"camera.pan": "world", DEPTH_UNIT: DEPTH_TAPER},
           "routes": [{"source": "hand:right.y", "target": "fx.warp.amount", "op": "push",
                       "value": 0.3}]}
    assert retaper_depths(doc, files) == (doc, [])
    assert UNITS[DEPTH_UNIT] == DEPTH_TAPER
    # a `units` that is not an object is no marker (as the pan's is not)
    odd = {"values": {}, "units": "world", "routes": [
        {"source": "hand:right.y", "target": "fx.warp.amount", "op": "push", "value": 0.3}]}
    out, moved = retaper_depths(odd, files)
    assert out["units"] == {DEPTH_UNIT: DEPTH_TAPER} and len(moved) == 1
    # and a second pass over the result finds nothing to do
    assert retaper_depths(out, files) == (out, [])


def test_an_old_preset_loads_as_the_tool_rewrites_it(tmp_path):
    """End to end: a corpus preset with the marker taken off and its depths
    put back to the numbers it held before this change loads through the
    app (`Presets.load_doc` converts, silently) and saves byte for byte
    as the tool writes it — which is the corpus file itself."""
    t = _tool()
    data = (CORPUS / "party-acid.json").read_bytes()
    doc = json.loads(data)
    assert doc["units"][DEPTH_UNIT] == DEPTH_TAPER
    del doc["units"][DEPTH_UNIT]
    before = {"fx.acid.bend": 0.6, "fx.acid.twist": 0.5, "fx.deconverge.amount": 0.6,
              "fx.wobble.amount": 0.5}
    for row in doc["routes"]:
        if row["target"] in before:
            row["value"] = before.pop(row["target"])
    assert not before
    old = tmp_path / "party-acid.json"
    old.write_text(preset.dumps(doc))
    again, notes, _ = headless.resave(old, tmp_path / "scratch")
    assert again == data and notes == []
    out, change = t.retaper(json.loads(old.read_text()), FxState().files, file=old.name)
    assert t.text(out).encode() == data and len(change.rows) == 4


def test_every_corpus_preset_is_marked_and_a_run_on_the_corpus_is_a_no_op(files):
    t = _tool()
    for path in sorted(CORPUS.glob("*.json")):
        doc = json.loads(path.read_text())
        assert t.marked(doc), path.name
        out, c = t.retaper(doc, files, file=path.name)
        assert out is doc and c.marked and not c.changed


def test_the_tool_dry_runs_then_writes_as_the_app_writes_and_backs_up_first(tmp_path, monkeypatch):
    """A dry run writes nothing and makes no backup; --write copies the
    library to the machine home first, rewrites every unmarked preset and
    patch as the app would save it (the marker in; a moved row in
    `Binding.to_json`'s spelling), leaves a marked one and a dot-file
    alone, and a second run changes nothing."""
    t = _tool()
    home, library = tmp_path / "home", tmp_path / "library"
    (library / "presets").mkdir(parents=True)
    (library / "patches").mkdir()
    (library / "shows").mkdir()
    monkeypatch.setenv("HYPERSPACE_HOME", str(home))
    src = json.loads((CORPUS / "party-noita.json").read_text())
    del src["units"][DEPTH_UNIT]
    for row in src["routes"]:
        if row["target"] == "fx.warp.amount":
            row["value"] = 0.3
        if row["target"] == "fx.tripcolour.amount":
            del row["value"]                      # a push of 1.0, omitted
    (library / "presets" / "party-noita.json").write_text(preset.dumps(src))
    done = json.loads((CORPUS / "party-trip.json").read_text())
    (library / "presets" / "party-trip.json").write_text(preset.dumps(done))
    (library / "presets" / ".party-noita.json.tmp").write_text("{}")
    patch = {"schema": "hyperspace.patch/1", "name": "wash", "nodes": ["wobble"], "wires": [],
             "values": {"fx.wobble.amount": 0.3},
             "routes": [{"source": "mod:1", "target": "fx.wobble.amount", "op": "push",
                         "value": 0.3}]}
    (library / "patches" / "wash.json").write_text(json.dumps(patch, indent=1) + "\n")
    (library / "bindings.json").write_text(json.dumps({"schema": "hyperspace.bindings/3", "bindings": [
        {"source": "axis:LX", "target": "fx.warp.amount", "op": "push", "value": 0.4},
        {"source": "cc:0:48", "target": "fx.warp.amount", "op": "abs"}]}))

    assert t.main(["--library", str(library)]) == 0
    assert json.loads((library / "presets" / "party-noita.json").read_text()) == src
    assert json.loads((library / "patches" / "wash.json").read_text()) == patch
    assert not list(home.glob("library-backup-*"))

    assert t.main(["--library", str(library), "--write", "--rows"]) == 0
    backups = list(home.glob("library-backup-*"))
    assert len(backups) == 1
    assert json.loads((backups[0] / "presets" / "party-noita.json").read_text()) == src
    text = (library / "presets" / "party-noita.json").read_text()
    out = json.loads(text)
    assert text == preset.dumps(out)                    # as the app writes it
    assert out["units"][DEPTH_UNIT] == DEPTH_TAPER
    rows = {r["target"]: r for r in out["routes"] if r["target"].startswith("fx.")}
    assert rows["fx.warp.amount"]["value"] != 0.3
    assert 0 < rows["fx.tripcolour.amount"]["value"] < 1        # the omitted 1.0, moved
    assert list(rows["fx.tripcolour.amount"]) == list(Binding.from_json(
        rows["fx.tripcolour.amount"]).to_json())                # in to_json's order
    for k in src:
        if k not in ("routes", "units"):
            assert out[k] == src[k]
    # the preset that was already marked: the same bytes
    assert (library / "presets" / "party-trip.json").read_text() == preset.dumps(done)
    assert (library / "presets" / ".party-noita.json.tmp").read_text() == "{}"
    # the patch: its push moved, the marker in, written as GRAPH writes one
    ptext = (library / "patches" / "wash.json").read_text()
    pout = json.loads(ptext)
    assert ptext == json.dumps(pout, indent=1) + "\n"
    assert pout["routes"][0]["value"] != 0.3 and pout["units"] == {DEPTH_UNIT: DEPTH_TAPER}
    # the session row is said, not rewritten
    said = t.session_rows(library, FxState().files)
    assert said == ["bindings.json: axis:LX → fx.warp.amount push 0.4"]
    assert json.loads((library / "bindings.json").read_text())["bindings"][0]["value"] == 0.4

    # a second run: nothing to do, nothing written, no second backup
    stamp = (library / "presets" / "party-noita.json").stat().st_mtime_ns
    assert t.main(["--library", str(library), "--write"]) == 0
    assert (library / "presets" / "party-noita.json").stat().st_mtime_ns == stamp
    assert (library / "presets" / "party-noita.json").read_text() == text
    assert len(list(home.glob("library-backup-*"))) == 2       # (a backup is made per --write)
