"""The parameter registry: one address space, one normalized contract."""

import math
from types import SimpleNamespace

import pytest
from conftest import CORPUS, seed

from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.bands import BANDS
from hyperspace.control import SCENES, Control
from hyperspace.geometry import SHAPES
from hyperspace.library import Library
from hyperspace.params import (
    PERFORMANCE_GROUPS,
    SESSION_GROUPS,
    Kind,
    Registry,
    build_registry,
    part_of,
)
from hyperspace.view import ViewState


def make(tmp_path):
    chain = Analyzer(Analyser())
    control = Control(chain)
    audio = SimpleNamespace(chain=chain)
    view = ViewState()
    seed(tmp_path)                  # the corpus: the shipped presets, the party and house shows
    lib = Library(tmp_path)
    presets = lib.project
    reg = build_registry(view, control, audio, presets)
    lib.attach(reg)
    return reg, view, control, audio, presets


@pytest.fixture()
def rig(tmp_path):
    return make(tmp_path)


def test_ids_are_unique_and_stable(rig):
    reg = rig[0]
    ids = reg.ids()
    assert len(ids) == len(set(ids))
    for must in ("view.bright", "view.shape", "master.gain", "scene.select",
                 "band.0.atk", "band.5.thr", "band.sel.pre", "band.select",
                 "preset.load.0", "preset.save.7", "camera.zoom", "view.plane.ZW"):
        assert must in reg, must
    r = Registry()
    r.toggle("x", "x", lambda: True, lambda v: None)
    with pytest.raises(ValueError):
        r.toggle("x", "x", lambda: True, lambda v: None)


def test_every_continuous_param_round_trips_norm(rig):
    """norm → set_norm → norm is the identity on every detent."""
    reg = rig[0]
    for p in reg:
        if p.kind is not Kind.CONTINUOUS:
            continue
        for pos in range(0, p.steps + 1, max(p.steps // 25, 1)):
            p.set_position(pos)
            assert p.position() == pos, f"{p.id} walks sideways at {pos}"
            u = p.norm
            p.set_norm(u)
            assert p.norm == pytest.approx(u, abs=1e-12), p.id
        p.set_norm(0.0)
        assert p.position() == 0
        p.set_norm(1.0)
        assert p.position() == p.steps


def test_tapered_param_quantizes_to_the_taper(rig):
    reg, view, *_ = rig
    b = reg["view.bright"]
    b.set_norm(0.5)
    assert b.position() == 50 and view.bright == b.taper.map(50)
    b.set_value(1.0)  # unity sits on the detent exactly
    assert b.position() == b.taper.unity and view.bright == 1.0
    b.set_value(999.0)  # clamped to the top of the throw
    assert b.position() == b.steps
    assert b.text() == "4.00×"


def test_raw_ranges_clamp_int_and_log(rig):
    reg, view, *_ = rig
    inst = reg["view.instances"]
    inst.set_norm(1.0)
    assert view.instances == 4096 and isinstance(view.instances, int)
    inst.set_value(-5)
    assert view.instances == 0          # the floor is zero (plan 16 WP5)
    inst.step(3)
    assert view.instances == 3
    z = reg["camera.zoom"]
    z.set_norm(0.5)  # log: halfway is the geometric middle — 1×, the range's ends about it
    assert view.zoom == pytest.approx(math.sqrt(z.lo * z.hi)) == pytest.approx(1.0)
    z.set_value(1.0)
    assert z.norm == pytest.approx(math.log2(1.0 / z.lo) / math.log2(z.hi / z.lo))
    yaw = reg["camera.yaw"]
    yaw.set_value(math.pi + 0.5)  # wraps, never clamps
    assert view.yaw == pytest.approx(-math.pi + 0.5)


def test_pitch_wraps_over_the_top_as_yaw_does(rig):
    """2026-10-14: the pitch is a whole turn that wraps (it stopped at
    ±1.55 before), so a stick or a drag held tumbles the shape round and
    round on both axes."""
    reg, view, *_ = rig
    pitch = reg["camera.pitch"]
    assert (pitch.lo, pitch.hi, pitch.wrap) == (-math.pi, math.pi, True)
    view.pitch = 0.0
    for _ in range(40):                   # a little over two whole turns, in steps
        pitch.nudge(0.35)
    assert view.pitch == pytest.approx(math.remainder(40 * 0.35, 2 * math.pi))
    pitch.set_value(-math.pi - 0.25)
    assert view.pitch == pytest.approx(math.pi - 0.25)


def test_instances_read_nothing_drawn_at_zero(rig):
    """Plan 16 WP5 (fork F3): zero at the very bottom of the throw, and a
    readout that says what a black render is. Since the instanced field:
    0–4096 on a count taper — every count to 64 one detent apart, then 40
    detents a doubling — whole numbers only, modulated or not."""
    from hyperspace.tapers import T_INSTANCES

    reg, view, *_ = rig
    inst = reg["view.instances"]
    assert (inst.lo, inst.hi) == (0, 4096) and inst.modulatable and inst.persist
    assert inst.taper is T_INSTANCES and inst.integer and inst.steps == 304
    assert view.instances == 1 and inst.text() == "1 instance(s)"     # the default stays 1
    inst.set_norm(0.0)                  # the knob's bottom, the slider's left end
    assert view.instances == 0 and isinstance(view.instances, int)
    assert inst.norm == 0.0 and inst.text() == "0 · nothing drawn"
    inst.step(1)
    assert view.instances == 1 and inst.text() == "1 instance(s)"
    for n in range(65):                 # every count to 64 is a detent
        inst.set_value(n)
        assert view.instances == n and inst.position() == n
    inst.step(40)                       # then 40 detents double it
    assert view.instances == 128 and inst.text() == "128 instance(s)"
    counts = [T_INSTANCES.map(p) for p in range(inst.steps + 1)]
    assert counts == sorted(set(counts)) and counts[-1] == 4096
    assert all(T_INSTANCES.unmap(c) == p for p, c in enumerate(counts))
    assert all(isinstance(T_INSTANCES.map(p + 0.37), int) for p in range(0, 304, 7))
    # a lane rides it in whole copies
    inst.set_value(10)
    inst.modulate(0.1)
    inst.apply()
    assert isinstance(view.instances, int) and view.instances == T_INSTANCES.map(10 + 30)
    inst.apply()                        # the lane let go: the base comes back
    assert view.instances == 10
    assert "0 draws nothing" in inst.tip
    # zero is a value like any other to a snapshot
    inst.set_value(0)
    snap = reg.snapshot("view")
    inst.set_value(7)
    reg.restore(snap)
    assert view.instances == 0


def test_nudge_and_scale_move_the_base_without_a_detent(rig):
    """Plan 09 WP2: the relative writers' two moves. In the param's own
    units, on the base, wrapped or clamped, returning what was applied —
    and never snapped to a detent, so a tapered param takes a fraction of
    a step per frame and adds it up."""
    reg, view, *_ = rig
    yaw, zoom, inst = reg["camera.yaw"], reg["camera.zoom"], reg["view.instances"]
    # wrap: the whole delta always lands
    yaw.set_value(math.pi - 0.1)
    assert yaw.nudge(0.3) == 0.3
    assert view.yaw == pytest.approx(-math.pi + 0.2)
    # clamp: what the stop let through
    zoom.set_value(zoom.hi - 1.0)
    assert zoom.nudge(5.0) == pytest.approx(1.0) and view.zoom == zoom.hi
    assert zoom.scale(2.0) == pytest.approx(1.0) and view.zoom == zoom.hi
    zoom.set_value(2.0)
    assert zoom.scale(1.5) == pytest.approx(1.5) and view.zoom == pytest.approx(3.0)
    assert zoom.nudge(-0.5) == pytest.approx(-0.5) and view.zoom == pytest.approx(2.5)
    # a ratio means nothing across zero: yaw's range does, a base of 0 does
    assert yaw.scale(2.0) == 1.0 and view.yaw == pytest.approx(-math.pi + 0.2)
    zoom.set_value(zoom.lo)
    assert zoom.scale(2.0) == pytest.approx(2.0)          # lo is above zero: fine
    # an integer range stays integer
    inst.set_value(4)
    assert inst.nudge(0.4) == 0 and view.instances == 4
    assert inst.nudge(0.6) == 1 and view.instances == 5
    # a tapered param: 20 sub-detent nudges add up to one detent's move
    d = reg["view.depth4"]
    d.set_position(80)
    one = d.taper.map(81) - d.taper.map(80)
    for _ in range(20):
        d.nudge(one / 20)
    assert view.depth4 == pytest.approx(d.taper.map(81), rel=1e-9) and d.position() == 81
    d.nudge(one / 20)
    assert view.depth4 > d.taper.map(81)                    # raw: not parked on the detent
    with pytest.raises(TypeError):
        reg["view.shape"].nudge(1)


def test_nudge_and_scale_under_modulation_move_the_base(rig):
    """While a source holds the param, nudge and scale write the base — a
    tapered one at a continuous position, so sub-detent moves still add
    up — and the offset rides on top through apply()."""
    reg, view, *_ = rig
    zoom, d = reg["camera.zoom"], reg["view.depth4"]
    zoom.set_value(1.0)
    d.set_position(80)
    one = d.taper.map(81) - d.taper.map(80)                  # a detent, in depth units
    for _ in range(10):
        zoom.scale(1.1)
        d.nudge(one / 20)
        zoom.modulate(0.1)
        d.modulate(0.1)
        reg.apply()
    assert zoom.base == pytest.approx(1.1 ** 10, rel=1e-9)
    assert zoom.eff_norm == pytest.approx(zoom.norm + 0.1, abs=1e-9)
    want = d.taper.map(80) + one / 2                         # linear in value: half a detent
    assert d.base == pytest.approx(want, rel=1e-9)
    assert 80.0 < d.norm * d.steps < 81.0                    # a continuous position
    assert view.depth4 == pytest.approx(d.taper.map(d.norm * d.steps + 16), rel=1e-9)  # + 0.1 × 160
    reg.apply()                                              # the source lets go
    assert view.zoom == pytest.approx(1.1 ** 10, rel=1e-9)
    assert view.depth4 == pytest.approx(want, rel=1e-9)


def test_enum_norm_and_stepping(rig):
    reg, view, *_ = rig
    s = reg["view.shape"]
    assert s.names == [x.name for x in SHAPES]
    s.set_norm(1.0)
    assert view.shape == len(SHAPES) - 1
    s.step(1)  # clamps at the end
    assert view.shape == len(SHAPES) - 1
    s.cycle(1)  # cycle wraps
    assert view.shape == 0
    s.set_norm(0.0)
    s.step(-1)
    assert view.shape == 0
    assert s.text() == SHAPES[0].name


def test_the_3d_switch_takes_the_fourth_dimension_out_of_the_view(rig):
    # plan 28: view.three_d is ViewState.three_d; integrate holds the 4D
    # pose (ViewState.body) and the renderer turns it in 3D
    reg, view, *_ = rig
    t = reg["view.three_d"]
    assert not view.three_d
    t.toggle()
    assert view.three_d and t.norm == 1.0
    # the pose it holds is folded into the view's body; a reset (the whole
    # view, or the 4D spin alone) takes it back out
    view.planes = [True] * 6
    view.integrate(0.5)
    assert view.held and view.body is not None
    reg["camera.reset"].fire()
    assert view.body is None and view.ang == [0.0] * 6
    view.integrate(0.5)
    reg["rot.reset_w"].fire()
    assert view.body is None and view.ang[3:] == [0.0, 0.0, 0.0]


def test_toggles_and_triggers(rig):
    reg, view, _control, *_ = rig
    f = reg["view.faces"]
    assert not view.faces
    f.toggle()
    assert view.faces and f.norm == 1.0
    f.set_norm(0.0)
    assert not view.faces
    f.step(1)
    assert view.faces
    zw = reg["view.plane.ZW"]
    zw.set(True)
    assert view.planes[5] is True
    view.yaw = 1.0
    reg["camera.reset"].fire()
    assert view.yaw == 0.0
    view.yaw = 1.0
    reg["camera.reset"].set_norm(1.0)  # a note-on fires a trigger
    assert view.yaw == 0.0
    view.yaw = 1.0
    reg["camera.reset"].set_norm(0.0)  # a note-off does not
    assert view.yaw == 1.0


def test_scene_and_band_params_route_through_control(rig):
    reg, _view, control, audio, _ = rig
    reg["scene.select"].set(4)
    assert control.scene == 4
    assert audio.chain.params[3].trim == -10  # Bass Engine's MID trim
    audio.chain.st[2]["e"] = 0.7
    reg["band.2.fn"].set(9)
    assert audio.chain.params[2].fn == 9 and audio.chain.st[2] == {}
    reg["band.3.atk"].set_norm(0.25)
    assert reg["band.3.atk"].position() == 36


def test_selected_band_alias_follows_selection(rig):
    reg, _view, control, audio, _ = rig
    control.selb = 1
    reg["band.sel.pre"].set_norm(1.0)
    assert audio.chain.params[1].pre == reg["band.1.pre"].value
    assert audio.chain.params[0].pre == 1  # untouched
    reg["band.select"].set(4)
    assert control.selb == 4
    assert reg["band.sel.atk"].value == audio.chain.params[4].atk
    assert reg["band.select"].names == [b.id for b in BANDS]


def test_params_survive_a_chain_swap(rig):
    """Getters resolve audio.chain live — a source attach replaces it."""
    reg, _view, control, audio, _ = rig
    new = Analyzer(Analyser())
    new.gain = 3.3
    audio.chain = new
    control.chain = new
    assert reg["master.gain"].value == 3.3
    reg["band.0.post"].set_norm(0.0)
    assert new.params[0].post == 0.0


def test_preset_bank_params(rig):
    """The bank's params (plan 13 WP2): select, load, save, next / prev
    over the project's preset names, loading through `Presets` (plan 19
    WP1: twenty-four choices, the F-keys' eight with a trigger each)."""
    from hyperspace.preset import Presets
    from hyperspace.routing import Bindings, Router

    reg, view, _control, _audio, bank = rig
    Presets(bank.lib, reg, Router(reg, Bindings()))
    bank.load("house", startup=False)          # the house moods (the seed opens party)
    assert reg["preset.select"].names[:2] == ["BIG BLUE WAVE", "EMBER ORBIT"]
    assert len(reg["preset.select"].names) == 24
    assert reg["preset.select"].names[8:] == [f"SLOT {k}" for k in range(9, 25)]
    reg["preset.load.1"].fire()
    assert bank.active == 1 and view.shape == 10
    reg["preset.select"].set_norm(0.0)
    assert bank.active == 0
    reg["preset.next"].fire()
    assert bank.active == 1
    reg["preset.prev"].fire()
    assert bank.active == 0
    view.shape = 12
    reg["preset.save.5"].fire()
    assert bank.bank[5] == "SPIRAL SILK"
    assert bank.lib.read("presets", "SPIRAL SILK")["values"]["view.shape"] == 12
    assert not reg["preset.save.5"].modulatable and not reg["preset.select"].persist


def test_the_list_triggers_walk_the_drop_downs_list_not_the_bank(rig):
    """`preset.list.next` / `prev` (the pad's B / X, 2026-10-14) step the
    PRESETS page's list — `Library.list`, by name — wrapping at both ends,
    and pass over the bank: a preset in no slot is reached, and one saved
    as new a moment ago is in the walk. QUANT's `preset.next` still walks
    only the bank's filled slots."""
    from hyperspace.library import PRESETS
    from hyperspace.preset import Presets
    from hyperspace.routing import Bindings, Router

    reg, _view, _control, _audio, bank = rig
    Presets(bank.lib, reg, Router(reg, Bindings()))
    bank.load("house", startup=False)
    lib = bank.lib
    listing = lib.list(PRESETS)
    assert len(listing) > 2 and set(listing) - set(bank.bank)   # some in no slot
    lib.load(PRESETS, listing[0])
    reg["preset.list.next"].fire()
    assert lib.current(PRESETS) == listing[1]
    reg["preset.list.prev"].fire()
    reg["preset.list.prev"].fire()                     # wraps to the end
    assert lib.current(PRESETS) == listing[-1]
    reg["preset.list.next"].fire()                     # …and back to the start
    assert lib.current(PRESETS) == listing[0]
    # a new save lands in the list at its name's place, and the walk finds it
    reg["preset.save_new"].fire()
    new = lib.current(PRESETS)
    assert new not in listing and new in lib.list(PRESETS)
    after = lib.list(PRESETS)
    reg["preset.list.next"].fire()
    assert lib.current(PRESETS) == after[(after.index(new) + 1) % len(after)]
    reg["preset.list.prev"].fire()
    assert lib.current(PRESETS) == new
    # the bank's walk is the desk's, unchanged: only filled slots
    reg["preset.select"].set_norm(0.0)
    reg["preset.next"].fire()
    assert lib.current(PRESETS) == bank.bank[bank.active] and bank.active >= 0


def test_the_list_walk_from_nothing_loaded_and_a_bad_file(rig):
    """With no preset loaded the walk starts at the list's first (next) or
    last (prev); a preset file that will not parse shows on the library's
    error line and the walk raises nothing."""
    from hyperspace.library import PRESETS
    from hyperspace.preset import Presets
    from hyperspace.routing import Bindings, Router

    reg, _view, _control, _audio, bank = rig
    Presets(bank.lib, reg, Router(reg, Bindings()))
    lib = bank.lib
    listing = lib.list(PRESETS)
    lib._current.pop(PRESETS, None)
    assert bank.walk(-1) == listing[-1]
    lib._current.pop(PRESETS, None)
    assert bank.walk(1) == listing[0]
    bad = lib.home / PRESETS / "aaa-broken.json"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text("{ not json")
    lib._current.pop(PRESETS, None)
    lib.error = ""
    assert bank.walk(1) is None and lib.error.startswith("library:")


def test_scene_names_match_presets(rig):
    assert rig[0]["scene.select"].names == list(SCENES)


def test_macro_knobs_are_persisted_attenuators_with_no_object(rig):
    """macro.1–8 (plan 09, decision 7): continuous 0–1, saved and drivable,
    read as a percentage, base 1 (the "× 1" a route runs at unscaled). They
    hold no object, so a snapshot is all there is to them: restoring one
    brings every knob back."""
    reg = rig[0]
    ms = reg.group("macro")
    assert [p.id for p in ms] == [f"macro.{k}" for k in range(1, 9)]
    for k, p in enumerate(ms, 1):
        assert (p.label, p.kind, p.lo, p.hi) == (f"Macro {k}", Kind.CONTINUOUS, 0.0, 1.0)
        assert p.persist and p.modulatable and not p.alias and p.taper is None
        assert p.value == 1.0 and p.text() == "100 %"
        assert "scale" in p.tip
    m = reg["macro.2"]
    m.set_value(0.42)
    assert m.text() == "42 %" and reg["macro.1"].value == 1.0   # its own slot
    snap = reg.snapshot("macro")
    assert snap == {f"macro.{k}": (0.42 if k == 2 else 1.0) for k in range(1, 9)}
    m.set_value(0.0)
    reg["macro.7"].set_norm(0.5)
    assert reg.restore(snap) == []
    assert m.value == pytest.approx(0.42) and reg["macro.7"].value == 1.0
    # the slot bounds itself: a restore writes raw, and nothing else would clamp
    assert reg.restore({"macro.3": 5.0, "macro.4": -2.0}) == []
    assert reg["macro.3"].value == 1.0 and reg["macro.4"].value == 0.0
    # performance state (plan 13 WP1): in the whole snapshot and its performance part
    assert set(reg.snapshot("macro")) == {p.id for p in ms}
    assert set(reg.snapshot("macro")) <= set(reg.snapshot(part="performance"))


def _full_registry(tmp_path):
    """Every param the app registers: build_registry, the hands setup, the
    clock, the LFOs, the render window's output and the desk's own pair
    over a table (headless)."""
    from hyperspace import hands, lfo, routing, tempo
    from hyperspace.overlay import Output

    reg = make(tmp_path)[0]
    routing.register_desk(reg, routing.Bindings())
    hands.register(reg, hands.HandSettings())
    clock = tempo.Clock()
    tempo.register(reg, clock)
    lfo.register(reg, lfo.LFOs(), clock)
    Output(None, None).register(reg)
    return reg


def test_every_persisted_group_is_performance_or_session(tmp_path):
    """Plan 13 §4 / exit criterion 1: every persisted param is in exactly
    one part, the two tuples are disjoint, and each persisted id's first
    segment is its group (Project._is_session splits an unattached file by it)."""
    reg = _full_registry(tmp_path)
    assert not set(PERFORMANCE_GROUPS) & set(SESSION_GROUPS)
    persisted = [p for p in reg if p.persist]
    for must in ("hands", "tempo", "lfo", "output", "macro", "band", "desk"):
        assert any(p.group == must for p in persisted), must
    # the desk (plan 18 WP2): knob smoothing is the session's and a show
    # keeps it; the layer latch beside it is still never saved
    assert part_of(reg["desk.slew"]) == "session" and reg["desk.slew"].persist
    assert not reg["desk.shift"].persist and "desk" in SESSION_GROUPS
    for p in persisted:
        assert (p.group in PERFORMANCE_GROUPS) + (p.group in SESSION_GROUPS) == 1, p.id
        assert part_of(p) in ("performance", "session"), p.id
        assert p.id.partition(".")[0] == p.group, p.id
    assert all(not p.persist for p in reg if p.id.startswith("rot.phase."))
    assert all(part_of(p) is None for p in reg.group("preset"))


def test_snapshot_by_part(tmp_path):
    """The performance and session parts partition the whole snapshot;
    the macros are in the whole one and in the performance part."""
    reg = _full_registry(tmp_path)
    whole = reg.snapshot()
    perf, sess = reg.snapshot(part="performance"), reg.snapshot(part="session")
    assert perf and sess and not set(perf) & set(sess)
    assert {**perf, **sess} == whole
    assert all(part_of(reg[k]) == "performance" for k in perf)
    assert all(part_of(reg[k]) == "session" for k in sess)
    macros = {f"macro.{k}" for k in range(1, 9)}
    assert macros <= set(whole) and macros <= set(perf)
    assert "tempo.bpm" in sess and "scene.select" in sess and "lfo.1.depth" in perf
    # the filters combine
    assert reg.snapshot("macro", part="session") == {}
    assert reg.snapshot("view", part="performance") == reg.snapshot("view")


def test_core_does_not_import_the_midi_adapter():
    """BLUEPRINT §3.6: the bridge depends on the core, never the reverse."""
    import sys

    sys.modules.pop("hyperspace.midi", None)
    import importlib

    for m in ("hyperspace.params", "hyperspace.control", "hyperspace.library",
              "hyperspace.bands", "hyperspace.render"):
        importlib.import_module(m)
    assert "hyperspace.midi" not in sys.modules


def test_a_non_finite_offset_never_poisons_a_base(rig):
    """Plan 14 WP1: `clamp` passed NaN through, a NaN offset became the base,
    and integer and enum params then raised in `reg.apply` every frame. A
    non-finite offset is dropped (and named on `reg.nonfinite`); the value
    stays the base, and the next clean frame is clean."""
    from hyperspace.tapers import clamp

    assert clamp(math.nan, 0.0, 1.0) == 0.0
    assert clamp(math.inf, 0.0, 1.0) == 1.0 and clamp(-math.inf, 0.0, 1.0) == 0.0
    reg, *_ = rig
    speed, shape, inst = reg["view.speed"], reg["view.shape"], reg["view.instances"]
    base_speed, base_shape, base_inst = speed.base, shape.base, inst.base
    for p in (speed, shape, inst):
        p.modulate(math.nan)
    inst.modulate(math.inf)
    reg.apply()                                   # no ValueError: NaN to integer
    assert sorted(reg.nonfinite) == ["view.instances", "view.shape", "view.speed"]
    assert speed.value == pytest.approx(base_speed)
    assert shape.value == base_shape and inst.value == base_inst
    for p in (speed, shape, inst):
        p.modulate(0.0)
    reg.apply()                                   # a clean frame
    assert reg.nonfinite == []
    assert math.isfinite(speed._base) and shape.value == base_shape
    reg.apply()                                   # the sources left: the base comes back
    assert speed.value == pytest.approx(base_speed) and not speed.modulated


def test_the_bank_adds_no_params(rig):
    """Plan 19 WP1's budget: a bank of twenty-four adds no param. The
    `preset` group is the 21 it was — select, a load and a save for each
    F-key, save-as, next, prev, home — and the list's next / prev
    (2026-10-14, the pad's B / X); slots 9–24 are choices of
    `preset.select`, which says which of them hold a preset (`Param.has`,
    what a pad's "filled" light reads)."""
    reg, _view, _control, _audio, bank = rig
    ids = [p.id for p in reg if p.group == "preset"]
    assert len(ids) == 23 and ids == [
        "preset.select",
        *[f"preset.{w}.{k}" for k in range(8) for w in ("load", "save")],
        "preset.save_new", "preset.next", "preset.prev",
        "preset.list.next", "preset.list.prev", "preset.home"]
    select = reg["preset.select"]
    assert len(select.names) == 24 == len(bank.bank)
    assert callable(select.has)
    assert [select.has(k) for k in range(24)] == [n is not None for n in bank.bank]
    assert select.has(8) and not select.has(9)             # the party show: TRACER on slot 9
    bank.bank[9], bank.bank[8] = "WAKE", None
    assert select.has(9) and not select.has(8)             # read live, never cached
    assert not select.has(-1) and not select.has(24)       # −1 is "nothing loaded"
    assert "twenty-four" in select.tip
    # only the bank's enum has the notion; `Registry.enum(has=)` stores it
    assert [p.id for p in reg if p.has is not None] == ["preset.select"]
    r = Registry()
    p = r.enum("x.pick", "Pick", lambda: 0, lambda v: None, ["a", "b"], has=lambda k: k == 1)
    assert p.has(1) and not p.has(0)
    assert r.enum("x.other", "Other", lambda: 0, lambda v: None, ["a"]).has is None


def test_inst_layout_is_declared(tmp_path):
    """Plan 20 WP6: `view.inst_layout`, three choices, default GRID, in the
    view group, persisted and modulatable like the motion beside it, and
    declared just before it. A layout change is one undo step; a preset
    that does not name the id — every file saved before this plan, the
    whole factory layer — loads it as GRID."""
    from test_undo import boot, frames, labels, settle

    from hyperspace.params import INST_LAYOUT

    reg, view, *_ = make(tmp_path / "plain")
    from hyperspace import field

    p = reg["view.inst_layout"]
    assert INST_LAYOUT == ["GRID", "HEX", "RING", "CUBIC", "BCC", "FCC", "HCP", "HEX PRISM",
                           "DIAMOND"] == field.NAMES
    assert p.kind is Kind.ENUM and p.names == INST_LAYOUT and p.label == "Layout"
    assert p.base == 0 and view.inst_layout == 0 and ViewState().inst_layout == 0
    assert p.group == "view" and p.persist and p.modulatable
    motion = reg["view.inst_motion"]
    assert (p.persist, p.modulatable) == (motion.persist, motion.modulatable)
    ids = reg.ids()
    assert ids.index("view.inst_layout") + 1 == ids.index("view.inst_motion")
    assert [reg[f"view.inst_{k}"].label for k in ("motion", "amp", "rate")] == [
        "Field motion", "Field amp", "Field rate"]
    # the instanced field's three: fit, spacing and a lattice's depth, after
    # the motion's, persisted and modulatable like it, off / 1 / 0.5 at rest
    fit, sp, de = (reg[f"view.inst_{k}"] for k in ("fit", "spacing", "persp"))
    assert ids.index("view.inst_rate") + 1 == ids.index("view.inst_fit")
    assert (fit.kind, sp.kind, de.kind) == (Kind.TOGGLE, Kind.CONTINUOUS, Kind.CONTINUOUS)
    assert all(q.group == "view" and q.persist and q.modulatable for q in (fit, sp, de))
    assert (fit.base, sp.base, de.base) == (False, 1.0, 0.5)
    assert (view.inst_fit, view.inst_spacing, view.inst_persp) == (False, 1.0, 0.5)
    p.set(2)
    assert view.inst_layout == 2 and reg.snapshot()["view.inst_layout"] == 2

    # a layout change is one undo step, with no code of its own
    r = boot(tmp_path / "home")
    settle(r)
    assert labels(r) == []
    lay = r.reg["view.inst_layout"]
    lay.set(1)
    settle(r)
    assert r.view.inst_layout == 1 and len(labels(r)) == 1
    r.reg["edit.undo"].fire()
    frames(r, 5)
    assert r.view.inst_layout == 0 and r.undo.stack == []

    # a preset that does not name it loads it as GRID: every corpus preset
    names = r.lib.list("presets")
    assert len(names) >= 5
    for name in names:
        lay.set(2)
        assert r.view.inst_layout == 2
        assert "view.inst_layout" not in r.presets.load(name), name
        assert r.view.inst_layout == 0 and lay.base == 0, name
    # (plan 36 T3: the corpus `/7` files are full saves — at its default;
    # their sources, made before it, never name it)
    import json

    sources = CORPUS.parent / "fixtures" / "factory-sources" / "presets"
    for f in sources.glob("*.json"):
        assert "inst_layout" not in f.read_text(), f.name
    for f in (CORPUS / "presets").glob("*.json"):
        assert json.loads(f.read_text())["values"].get("view.inst_layout", 0) == 0, f.name


# ---- plan 26 A0: the naming rule for node instances (ENGINEERING §2) ----

def test_the_first_instance_keeps_todays_id_and_extras_carry_a_marker():
    """The first instance of a node is today's id; instance n ≥ 2 carries
    n as a segment right after the node's prefix, never a new first
    segment; `instance_of` reads either back."""
    from hyperspace.params import instance_id, instance_of

    for node, key in (("fx.acid", "mix"), ("ghost", "alpha"), ("dream", "mix")):
        assert instance_id(node, key) == instance_id(node, key, 1) == f"{node}.{key}"
        assert instance_of(f"{node}.{key}", node) == (1, key)
        for n in (2, 3, 12):
            pid = instance_id(node, key, n)
            assert pid.split(".")[0] == node.split(".")[0]          # the group stays
            assert instance_of(pid, node) == (n, key)
    assert instance_id("fx.acid", "mix", 2) == "fx.acid.2.mix"
    assert instance_id("ghost", "alpha", 2) == "ghost.2.alpha"
    assert instance_of("fx.acid.mix", "fx.warp") is None
    # an explicit `.1.` is never written, so it reads as a key, by design
    assert instance_of("fx.acid.1.mix", "fx.acid") == (1, "1.mix")
    with pytest.raises(ValueError):
        instance_id("fx.acid", "mix", 0)


def test_every_node_param_today_reads_as_its_first_instance():
    """No preset or binding migrates for a single-instance graph: every
    effect's, the hands' and the dream's params as registered today read
    back as instance 1 under their own id, their group is their id's
    first segment (so an extra instance lands in the same part of a
    preset), and no effect file or key is purely decimal (which would
    read as a marker)."""
    from hyperspace.fx import FxState
    from hyperspace.ghost import GhostState
    from hyperspace.lookback import DreamState
    from hyperspace.params import instance_of

    chain = Analyzer(Analyser())
    fx = FxState()
    reg = build_registry(ViewState(), Control(chain), SimpleNamespace(chain=chain), None,
                         DreamState(), fx, ghost=GhostState())
    nodes = [f"fx.{name}" for name in fx.names()] + ["ghost", "dream"]
    assert len(nodes) > 2
    assert not any(name.isdecimal() for name in fx.names())
    seen = set()
    for p in reg:
        for node in nodes:
            got = instance_of(p.id, node)
            if got is None:
                continue
            n, key = got
            assert n == 1 and f"{node}.{key}" == p.id, p.id
            assert not key.split(".")[0].isdecimal(), p.id
            assert p.group == p.id.split(".")[0], (p.id, p.group)
            seen.add(node)
    assert seen == set(nodes)
