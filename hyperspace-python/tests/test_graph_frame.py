"""Plan 35 B, M (T2): the builder and today's frame as wires.

`graph.build_graph` builds a wired frame from its wires alone — nothing
unreached, one end (`Shown`) per picture, the mutes read per window each
frame and never a rebuild, copies (`Copy`) with their originals' knobs and
the stand-down of a copy chain over a hands composite. `graphmigrate.
frame_wires` / `output_wires` write today's frame (`default_graph` from
the switches) as those wires, and `signature` proves the two equal node
for node over every golden case (Review Focus 1) — against the live
`default_graph` and against the recorded reference
(`tests/fixtures/frame-signatures.json`, `tools/golden_frames.py
--signatures`), which T4 keeps when the switch half goes.

The GL half (the mutes' pixels, the stand-down, the one end) draws through
the golden tool's rig with two synthetic hands, and skips without a
standalone context."""

from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from hyperspace import graph as G
from hyperspace import graphmigrate as M
from hyperspace.outputs import Switches, View

ROOT = Path(__file__).resolve().parents[1]
SIZE = (240, 150)


def _tool():
    if "golden_frames" in sys.modules:
        return sys.modules["golden_frames"]
    spec = importlib.util.spec_from_file_location("golden_frames",
                                                  ROOT / "tools" / "golden_frames.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["golden_frames"] = mod
    spec.loader.exec_module(mod)
    return mod


def w(a, b):
    return {"from": a, "to": b}


def wires_of(pairs):
    return [w(a, b) for a, b in pairs]


def wired(*pairs, nodes=()):
    return {"frame": "wired", "nodes": list(nodes), "wires": wires_of(pairs)}


def views(n=2, **sw):
    return [View(Switches(**sw), SIZE) for _ in range(n)]


def the_frame(section: dict | None = None, **kw) -> dict:
    """`section` (an old one, before the wired frame) as `migrate` will
    land it from T3: renamed, then written as a wired frame."""
    section = section or {}
    return M.wired_section(M.renamed(section), G.read_graph(section), **kw)


# ---------------------------------------------------------------- frame_wires

def test_frame_wires_of_the_default_section():
    entries, got = M.frame_wires(G.read_graph({}))
    assert entries == []
    assert got == wires_of([("shape", "scene.geometry"), ("scene", "lookback.image"),
                            ("lookback", "output.all.image"),
                            ("hands.layer", "output.all.hands"),
                            ("hands.layer", "output.all.guide"),
                            ("scene", "lookback.capture")])


RUN = {"wires": wires_of([("frame", "acid.image"), ("acid", "palette.image"),
                          ("palette", "fx.image")])}
BACK = {"wires": wires_of([("frame", "fx.image"), ("media.c", "backdrop.image")])}
VARIANTS = {
    "run": (RUN, {}, [], [
        ("shape", "scene.geometry"), ("scene", "lookback.image"), ("lookback", "acid.image"),
        ("acid", "palette.image"), ("palette", "output.all.image"),
        ("hands.layer", "output.all.hands"), ("hands.layer", "output.all.guide"),
        ("scene", "lookback.capture")]),
    "backdrop": (BACK, {}, [], [
        ("shape", "scene.geometry"), ("scene", "backdrop.scene"), ("backdrop", "lookback.image"),
        ("scene", "lookback.occluder"), ("lookback", "output.all.image"),
        ("hands.layer", "output.all.hands"), ("hands.layer", "output.all.guide"),
        ("scene", "lookback.capture")]),
    "backdrop.history": (BACK, {"backdrop_history": True}, [], [
        ("shape", "scene.geometry"), ("scene", "backdrop.scene"), ("backdrop", "lookback.image"),
        ("lookback", "output.all.image"), ("hands.layer", "output.all.hands"),
        ("hands.layer", "output.all.guide"), ("backdrop", "lookback.capture")]),
    "holds": ({"nodes": [{"kind": "history", "holds": "scene+hands"}]}, {},
              [{"kind": "composite"}], [
        ("shape", "scene.geometry"), ("scene", "lookback.image"),
        ("lookback", "output.all.image"), ("hands.layer", "output.all.hands"),
        ("hands.layer", "output.all.guide"), ("scene", "composite.under"),
        ("hands.layer", "composite.over"), ("composite", "lookback.capture")]),
    "in-scene": ({"nodes": [{"kind": "hands", "into": "scene"}]}, {}, [], [
        ("hands", "scene.geometry"), ("shape", "scene.geometry"), ("scene", "lookback.image"),
        ("lookback", "output.all.image"), ("hands.guide", "output.all.guide"),
        ("scene", "lookback.capture")]),
    "depth": ({"nodes": [{"kind": "hands", "laid": "depth"}]}, {}, [], [
        ("shape", "scene.geometry"), ("scene", "lookback.image"),
        ("lookback", "output.all.image"), ("hands.layer", "output.all.hands"),
        ("hands.layer", "output.all.guide"), ("scene", "lookback.capture")]),
    "holds+depth": ({"nodes": [{"kind": "history", "holds": "scene+hands"},
                               {"kind": "hands", "laid": "depth"}]}, {},
                    [{"kind": "composite", "blend": "depth"}], [
        ("shape", "scene.geometry"), ("scene", "lookback.image"),
        ("lookback", "output.all.image"), ("hands.layer", "output.all.hands"),
        ("hands.layer", "output.all.guide"), ("scene", "composite.under"),
        ("hands.layer", "composite.over"), ("composite", "lookback.capture")]),
}


@pytest.mark.parametrize("name", sorted(VARIANTS))
def test_frame_wires_variants(name):
    section, kw, entries, pairs = VARIANTS[name]
    got_entries, got = M.frame_wires(G.read_graph(section), **kw)
    assert got_entries == entries
    assert got == wires_of(pairs)


def test_the_wired_section_reads_as_a_wired_frame():
    """`wired_section`: the marker first, the run's wires gone (`frame`
    and `fx` named nowhere), the hands' `into` and the look-back's `holds`
    taken out (they are wires now), the frame appended; it reads with no
    note."""
    sec = {"nodes": [{"kind": "hands", "into": "scene", "draw": "lines"},
                     {"kind": "hands", "instance": 2},
                     {"kind": "history", "holds": "scene+hands"}],
           "wires": [*RUN["wires"], w("hands.2", "output.2.hands")]}
    got = the_frame(sec)
    assert list(got) == ["frame", "nodes", "wires"]
    assert got["nodes"] == [{"kind": "hands", "draw": "lines"}, {"kind": "hands", "instance": 2}]
    assert not any(x in ("frame", "fx") for e in got["wires"]
                   for x in (e["from"], e["to"].rpartition(".")[0]))
    assert got["wires"][0] == w("hands.2.layer", "output.2.hands")
    spec = G.read_graph(got)
    assert spec.wired and spec.notes == ()


# ---------------------------------------------------------------- output_wires

ACID = {"wires": wires_of([("frame", "acid.image"), ("acid", "fx.image")])}
THROUGH = [{"kind": "composite"}, {"kind": "copy", "of": "acid"},
           w("lookback", "composite.under"), w("hands.layer", "composite.over"),
           w("composite", "copy.image"), w("copy", "output.N.image"),
           w("ground", "output.N.hands")]
STATES = {
    (True, True, False): [],
    (True, True, True): THROUGH,
    (True, False, False): [w("ground", "output.N.hands"), w("ground", "output.N.guide")],
    (True, False, True): [w("ground", "output.N.hands"), w("ground", "output.N.guide")],
    (False, True, False): [w("ground", "output.N.image")],
    (False, True, True): [e for e in THROUGH if e != w("lookback", "composite.under")],
    (False, False, False): [w("ground", "output.N.image"), w("ground", "output.N.hands"),
                            w("ground", "output.N.guide")],
    (False, False, True): [w("ground", "output.N.image"), w("ground", "output.N.hands"),
                           w("ground", "output.N.guide")],
}


def _for(n: int, got: list[dict]) -> list[dict]:
    return [{k: v.replace("output.N.", f"output.{n}.") for k, v in e.items()} for e in got]


@pytest.mark.parametrize("state", sorted(STATES))
def test_output_wires_for_each_state(state):
    """The eight `Shows` against today's `outputs.route` table, output 3 of
    the default section with the run `acid`."""
    spec = G.read_graph(the_frame(ACID))
    shows = M.Shows(*state)
    assert M.output_wires(spec, 3, shows) == _for(3, STATES[state])


def test_through_with_an_empty_run_writes_the_composite_alone():
    spec = G.read_graph(the_frame({}))
    assert M.output_wires(spec, 2, M.Shows(through=True)) == [
        {"kind": "composite"}, w("lookback", "composite.under"),
        w("hands.layer", "composite.over"), w("composite", "output.2.image"),
        w("ground", "output.2.hands")]


def test_two_throughs_take_their_own_instances():
    sec = the_frame(ACID)
    sec = M.with_output_wires(sec, 2, M.Shows(through=True))
    got = M.output_wires(G.read_graph(sec), 3, M.Shows(scene=False, through=True))
    assert got[:2] == [{"kind": "composite", "instance": 2},
                       {"kind": "copy", "of": "acid", "instance": 2}]
    assert G.read_graph(M.with_output_wires(sec, 3, M.Shows(scene=False, through=True))
                        ).notes == ()


# ---------------------------------------------------------------- Review Focus 1

@pytest.fixture(scope="module")
def loader():
    got = _tool().Loader()
    yield got
    got.close()


@pytest.fixture(scope="module")
def recorded():
    path = _tool().SIGNATURES
    return json.loads(path.read_text()) if path.exists() else None


@pytest.mark.parametrize("key", _tool().signature_keys())
def test_the_wired_frame_builds_what_default_graph_builds(loader, recorded, key):
    """Every factory preset and fixture in the eight states (eight views at
    once, as the golden rig draws them), each WIRED variant over its
    presets and states, the window alone and the clouded rigs: the
    document through the load's migration, then `wired_section` and each
    view's `output_wires`, built by `build_graph` with every mute on — node
    for node the frame `default_graph` built from the switches, as recorded
    (`tests/fixtures/frame-signatures.json`). Plan 35 T4 deleted the
    oracle: the file is the reference now, every case unchanged."""
    tool = _tool()
    assert recorded is not None and key in recorded, key
    case = tool.signature_case(loader, key)
    new, _ = tool.frame_graphs(*case)
    assert tool.as_json(G.signature(new)) == recorded[key]
    assert new.key == (len(case[0]),)


def test_the_reference_is_recorded():
    """`tools/golden_frames.py --signatures` wrote every case (T4 compares
    against the file alone)."""
    tool = _tool()
    assert set(json.loads(tool.SIGNATURES.read_text())) == set(tool.signature_keys())


# ---------------------------------------------------------------- Review Focus 2

def test_nothing_unreached_is_built():
    g = G.build_graph(views(), G.read_graph(G.read_graph({"frame": "wired"}).to_json()).wiring())
    assert g.order and all(isinstance(n, G.Output) for n in g.order)
    g = G.build_graph(views(), G.read_graph(wired(("shape", "scene.geometry"))).wiring())
    assert all(isinstance(n, G.Output) for n in g.order)
    assert g.run == () and not g.reads_ring


def test_a_scene_on_a_backdrop_is_drawn_see_through():
    on = wired(("shape", "scene.geometry"), ("channel.a", "backdrop.image"),
               ("scene", "backdrop.scene"), ("backdrop", "output.all.image"))
    g = G.build_graph(views(1), G.read_graph(on).wiring())
    assert g.nodes["scene"].ground == 0.0
    alone = wired(("shape", "scene.geometry"), ("scene", "output.all.image"))
    g = G.build_graph(views(1), G.read_graph(alone).wiring())
    assert g.nodes["scene"].ground is None


def test_the_capture_runs_once_after_every_end():
    sec = wired(("shape", "scene.geometry"), ("scene", "lookback.image"),
                ("lookback", "output.all.image"), ("channel.a", "output.2.image"),
                ("scene", "delay.image"), ("delay", "output.3.image"),
                ("scene", "lookback.capture"), nodes=[{"kind": "delay"}])
    g = G.build_graph(views(3), G.read_graph(sec).wiring())
    caps = [n for n in g.order if isinstance(n, G.Capture)]
    assert len(caps) == 1
    cap = caps[0]
    later = [n for n in g.order if isinstance(n, (G.Shown, G.DelayWrite))]
    assert len(later) == 4                        # three ends and the delay's write
    at = g.order.index(cap)
    assert all(g.order.index(n) < at for n in later)
    assert set(map(id, later)) <= set(map(id, cap.after))
    assert all(cap in out.after for out in g.outputs)


def test_a_copy_reads_its_originals_knobs():
    c = G.Copy("copy", "acid")
    assert c.effect == "acid" and c.name == "copy" and c.placed == "wire"


def test_one_end_for_two_outputs_of_one_picture_is_built_once():
    g = G.build_graph(views(2), G.read_graph(the_frame({})).wiring())
    ends = [n for n in g.order if isinstance(n, G.Shown)]
    assert len(ends) == 1
    assert all(out.inputs["image"] is ends[0] for out in g.outputs)


def test_the_hands_guide_is_its_layers_own_while_the_layer_is_built():
    """`hands.guide` is the layer's split-out guide while `hands.layer` is
    built (the default graph's `scene_readout`), else the guide alone."""
    alone = the_frame({"nodes": [{"kind": "hands", "into": "scene"}]})
    g = G.build_graph(views(1), G.read_graph(alone).wiring())
    assert isinstance(g.outputs[0].inputs["readout"], G.Readout)
    both = M.with_output_wires(alone, 2, M.Shows(scene=False))
    g = G.build_graph(views(2), G.read_graph(both).wiring())
    layer = g.outputs[1].inputs["hands"]
    assert isinstance(layer, G.HandsLayer) and g.outputs[0].inputs["readout"] is layer
    assert layer.readout == "always"              # the hands are in the scene too


# ---------------------------------------------------------------- the GL half

@pytest.fixture(scope="module")
def ctx():
    try:
        import moderngl

        c = moderngl.create_context(standalone=True)
    except Exception as e:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {e}")
    yield c


@pytest.fixture(scope="module")
def rig(ctx):
    """legacy6 with two synthetic hands present (the golden rig), its
    wiring replaced per test."""
    got = _tool().Rig("legacy6", "present", ctx)
    yield got
    got.close()


def _fbo(ctx):
    return ctx.framebuffer(color_attachments=[ctx.renderbuffer(SIZE, 4)])


def _px(f) -> np.ndarray:
    w_, h_ = f.size
    return np.frombuffer(f.read(components=4), np.uint8).reshape(h_, w_, 4)[::-1].astype(int)


def _land(rig, section: dict) -> None:
    spec = G.read_graph(section, effects={e.partition(".")[0] for e in rig.fx.specs})
    assert spec.notes == (), spec.notes
    rig.renderer.wiring = spec.wiring()


def _draw(ctx, rig, switches, frames=3):
    vs = [View(sw, SIZE, target=_fbo(ctx)) for sw in switches]
    for _ in range(frames):
        rig.frame(vs, SIZE, 1.0)
    assert ctx.error == "GL_NO_ERROR"
    for v in vs:
        assert not v.error, v.error
    return [_px(v.target) for v in vs]


def test_a_mute_ignores_its_port(ctx, rig):
    """The default frame wired: a window whose picture is muted shows the
    ground with the hands laid over — pixel for pixel the window whose
    section wires `ground → output.2.image`; one whose hands are muted
    shows no layer and no guide — the window wired `ground` into its hands
    and guide."""
    sec = the_frame({})
    sec["wires"] += wires_of([("ground", "output.2.image"), ("ground", "output.4.hands"),
                              ("ground", "output.4.guide"), ("ground", "output.5.image"),
                              ("ground", "output.5.hands"), ("ground", "output.5.guide")])
    _land(rig, sec)
    muted, wired_, hands_off, no_hands, black, plain = _draw(
        ctx, rig, [Switches(scene=False), Switches(), Switches(hands=False), Switches(),
                   Switches(), Switches()])
    assert rig.renderer.stats["layer"]                    # a hand drew
    assert np.array_equal(muted, wired_)
    assert not np.array_equal(muted, black)               # the hands, laid over the ground
    assert np.array_equal(hands_off, no_hands)
    assert not np.array_equal(hands_off, plain)           # and the layer is gone


def test_a_mute_never_rebuilds(ctx, rig):
    _land(rig, the_frame({}))
    vs = [View(Switches(), SIZE, target=_fbo(ctx)) for _ in range(2)]
    first = rig.renderer._graph_for(vs)
    for k in range(4):
        vs[1].switches = replace(vs[1].switches, scene=k % 2 == 0)
        rig.frame(vs, SIZE, 1.0)
        assert rig.renderer._graph_for(vs) is first


def test_one_end_for_two_outputs_of_one_picture(ctx, rig):
    """Two windows taking All outputs' picture share one end, painted once
    into a frame texture; with one window's picture muted the other is
    painted direct again — no rebuild."""
    _land(rig, the_frame({}))
    _draw(ctx, rig, [Switches(), Switches()], frames=1)
    assert rig.renderer.stats["direct"] is False
    assert rig.renderer.stats["ends"] == ["shown(lookback)"]
    _draw(ctx, rig, [Switches(), Switches(scene=False)], frames=1)
    assert rig.renderer.stats["direct"] is True


STAND = wired(("shape", "scene.geometry"), ("scene", "lookback.image"),
              ("scene", "lookback.capture"), ("lookback", "acid.image"),
              ("acid", "output.all.image"), ("hands.layer", "output.all.hands"),
              ("hands.layer", "output.all.guide"), ("lookback", "composite.under"),
              ("hands.layer", "composite.over"), ("composite", "copy.image"),
              ("copy", "output.2.image"), ("ground", "output.2.hands"),
              nodes=[{"kind": "composite"}, {"kind": "copy", "of": "acid"}])


def _acid(rig, on: bool) -> None:
    rig.reg["fx.on"].set(True)
    rig.reg["fx.acid.on"].set(on)
    rig.reg["fx.acid.mix"].set(1.0)


def test_a_copy_reads_its_originals_knobs_when_drawn(ctx, rig):
    """With `fx.acid.on` off both `acid` and its copy read through (no
    pass); on, each runs its own pass."""
    _land(rig, STAND)
    _acid(rig, False)
    _draw(ctx, rig, [Switches(), Switches()], frames=1)
    assert not ({"acid", "copy"} & set(rig.renderer.stats["effects"]))
    _acid(rig, True)
    _draw(ctx, rig, [Switches(), Switches()], frames=1)
    assert {"acid", "copy"} <= set(rig.renderer.stats["effects"])
    _acid(rig, False)


def test_a_copy_chain_stands_down(ctx, rig):
    """Output 2's picture is a copy of acid over the look-back with the
    hands laid on: with acid off it stands down to acid's end with the
    layer laid over at the output; with acid on and a hand drawn it shows
    its own end."""
    _land(rig, STAND)
    g = G.build_graph([View(Switches(), SIZE)] * 2, rig.renderer.wiring, (),
                      tuple(sorted(rig.fx.specs)))
    end = g.outputs[1].inputs["image"]
    assert isinstance(end, G.Shown) and end.stands and end.fallback is g.outputs[0].inputs["image"]
    _acid(rig, False)
    _draw(ctx, rig, [Switches(), Switches()], frames=1)
    assert rig.renderer.stats["routes"][1] == ("shown(acid)", True)
    _acid(rig, True)
    _draw(ctx, rig, [Switches(), Switches()], frames=1)
    assert rig.renderer.stats["layer"]
    assert rig.renderer.stats["routes"][1] == ("shown(copy)", False)
    _acid(rig, False)


# ---------------------------------------------------------------- T3: R9, and a stronger proof

def test_a_hands_mute_wins_over_a_stand_down():
    """Ruling R9 (plan 35 T3): a stand-down lays its layer over at the
    output — but not on a window whose hands are muted: a mute mutes."""
    sec = M.with_output_wires(the_frame(ACID), 1, M.Shows(through=True))
    g = G.build_graph(views(1), G.read_graph(sec).wiring(), (), ("acid",))
    out = g.outputs[0]
    end = out.inputs["image"]
    assert isinstance(end, G.Shown) and end.stands
    layer = end.layer
    end.bent = lambda frame: False                     # nothing live: it stands down
    layer.image = lambda frame: "a hand"               # and a hand is drawn

    def frame(**sw):
        from types import SimpleNamespace
        return SimpleNamespace(data={}, views=[View(Switches(**sw), SIZE)])

    shown, laid = out.settle(frame())
    assert shown is end.fallback and laid == (layer, "over")
    shown, laid = out.settle(frame(hands=False))
    assert shown is end.fallback and laid is None


def test_laid_on_a_second_hands_entry_reads_in_a_wired_frame():
    """Carried from T2: in a wired frame any hands node may have a layer, so
    `laid` sits on the entry whose layer is laid — hands 2's here (hands 1
    in the scene, hands 2 the layer laid depth-aware), migrated and read
    with no note, said back on the same entry, and built depth-aware."""
    old = {"nodes": [{"kind": "hands", "into": "scene"},
                     {"kind": "hands", "instance": 2, "laid": "depth"}]}
    assert G.read_graph(old).laid == "depth"
    sec, notes = M.migrate({"values": {}, "graph": old}, {})
    spec = G.read_graph(sec["graph"])
    assert notes == [] and spec.notes == () and spec.wired
    assert (spec.laid, spec.laid_on) == ("depth", 2)
    assert {"kind": "hands", "instance": 2, "laid": "depth"} in spec.to_json()["nodes"]
    again = G.read_graph(spec.to_json())
    assert (again.laid, again.laid_on) == ("depth", 2) and again.to_json() == spec.to_json()
    g = G.build_graph(views(1), spec.wiring())
    assert g.outputs[0].blend == "depth"
    with pytest.raises(G.GraphError, match="laid twice"):
        G.read_graph(wired(nodes=[{"kind": "hands", "laid": "add"},
                                  {"kind": "hands", "instance": 2, "laid": "depth"}]))


def test_the_signature_follows_every_picture_port():
    """Before T4 deletes `default_graph`, `signature` follows every port a
    picture comes in by — an effect's `aux`, a switch's `inN`, a
    composite's `depth`, the look-back's `occluder`, the scene's geometry
    — and names it, so two frames that differ only there differ."""
    def sig(*pairs, nodes=()):
        spec = G.read_graph(wired(*pairs, nodes=nodes))
        assert not spec.notes, spec.notes
        return G.signature(G.build_graph(views(1), spec.wiring(), (), ("acid",)))

    out = ("acid", "output.all.image")
    assert (sig(("channel.a", "acid.image"), ("channel.b", "acid.aux"), out)
            != sig(("channel.b", "acid.image"), ("channel.a", "acid.aux"), out))
    scene = (("shape", "scene.geometry"), ("scene", "lookback.image"),
             ("lookback", "acid.image"), out)
    assert sig(*scene, ("scene", "acid.aux")) != sig(*scene, ("lookback", "acid.aux"))
    assert "aux" in json.dumps(_tool().as_json(sig(*scene, ("scene", "acid.aux"))))
    sw = [{"kind": "switch"}]
    assert (sig(("channel.a", "switch.in1"), ("channel.b", "switch.in2"),
                ("switch", "output.all.image"), nodes=sw)
            != sig(("channel.b", "switch.in1"), ("channel.a", "switch.in2"),
                   ("switch", "output.all.image"), nodes=sw))
    assert (sig(("hands", "scene.geometry"), *scene)
            != sig(("hands.2", "scene.geometry"), *scene, nodes=[{"kind": "hands",
                                                                  "instance": 2}]))


def test_the_signature_follows_what_the_sinks_read():
    """T3 review: two frames alike but for what the look-back records
    (`scene` or `backdrop → lookback.capture`), or what a delay writes,
    differ in `signature` — the sinks are read by their chains."""
    head = (("shape", "scene.geometry"), ("channel.a", "backdrop.image"),
            ("scene", "backdrop.scene"), ("backdrop", "lookback.image"),
            ("lookback", "output.all.image"))

    def sig(*pairs, nodes=()):
        spec = G.read_graph(wired(*head, *pairs, nodes=nodes))
        assert not spec.notes, spec.notes
        # (two windows: a wire into an output not open builds nothing, T4)
        return G.signature(G.build_graph(views(2), spec.wiring()))

    assert sig(("scene", "lookback.capture")) != sig(("backdrop", "lookback.capture"))
    d = [{"kind": "delay"}]
    assert (sig(("scene", "delay.image"), ("delay", "output.2.image"), nodes=d)
            != sig(("backdrop", "delay.image"), ("delay", "output.2.image"), nodes=d))


def test_the_proof_covers_one_window_and_the_clouds():
    """The window's own frame alone (`SOLO`, and `SOLO_FX` for a preset
    with an effect on) and the recorded point cloud (`CLOUDED`) are cases
    of the proof too, recorded from `default_graph`."""
    keys = set(_tool().signature_keys())
    assert {"legacy6/solo", "party-trip/solo", "party-trip/solo-scene+hands+through",
            "legacy6/cloud", "party-faces/cloud"} <= keys
    assert "legacy6/solo-scene+hands+through" not in keys
