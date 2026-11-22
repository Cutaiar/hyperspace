"""Plan 65: the effect previews (`previews.EffectPreviews`) — every effect
file through the test card, a still and a short loop, for GRAPH's effect
picker.

Held here: nothing is made until asked, and never more than the budget a
frame; the stills come first, a loop only for the tile asked; a file whose
program changes is made again and a file that goes is freed; the show's
values and its outputs' bytes are untouched; the families and the search
are read from the files' metadata; and all the files fit in the memory the
plan states."""

from __future__ import annotations

import shutil

import numpy as np
import pytest
from test_thumbnails import SIZE, S, _px, _renderer, _views

from hyperspace import fx
from hyperspace import previews as pv
from hyperspace.fx import FxState


def _cache(ctx, directory=None, budget=pv.PASSES_PER_FRAME):
    st = FxState(directory) if directory is not None else FxState()
    return pv.EffectPreviews(st, ctx, budget=budget), st


def _cell(cache, name, k=0) -> np.ndarray:
    tex = cache.atlas[name][0]
    a = np.frombuffer(tex.read(), np.uint8).reshape(pv.ATLAS_H, pv.ATLAS_W, 4)
    x, y, w, h = pv.cell_rect(k)
    return a[y:y + h, x:x + w].astype(int)


def _until_done(cache, names, loop=None, frames=400) -> int:
    """`make` once a frame, the page wanting `names`, until a frame makes
    nothing; the frames it took."""
    for k in range(frames):
        cache.want(names, loop=loop)
        if cache.make() == 0:
            return k
    raise AssertionError("never settled")


# ---------------------------------------------------------------- the budget

def test_nothing_is_made_until_asked_and_no_gl_object_before(ctx):
    cache, _ = _cache(ctx)
    assert cache.make() == 0 and cache.atlas == {} and cache._chain is None
    assert cache.picture("wave") is None


def test_never_more_than_the_budget_a_frame_and_the_stills_first(ctx):
    cache, st = _cache(ctx)
    names = sorted(st.files)
    runs = []
    for _ in range(40):
        cache.want(names, loop="wave")
        runs.append(cache.make())
        assert not cache.error
    assert max(runs) == pv.PASSES_PER_FRAME
    # the card (1) and every still (27) before any of the loop's cells
    stills = -(-(1 + len(names)) // pv.PASSES_PER_FRAME)
    assert all(r == pv.PASSES_PER_FRAME for r in runs[:stills - 1])
    loop_done = stills + -(-pv.LOOP_FRAMES // pv.PASSES_PER_FRAME) + 1
    assert all(r == 0 for r in runs[loop_done:])
    assert all(cache.made[n] == {0} for n in names if n != "wave")
    assert cache.looped("wave") and cache.made["wave"] == set(range(pv.LOOP_FRAMES + 1))


def test_a_loop_is_made_only_for_the_tile_asked(ctx):
    cache, _ = _cache(ctx, budget=1000)
    cache.want(["acid", "wave"])
    cache.make()
    assert cache.made["acid"] == cache.made["wave"] == {0}
    assert cache.picture("wave", t=0.3) is not None        # the still, the loop not made
    assert not cache.looped("wave")
    cache.want(["acid", "wave"], loop="wave")
    cache.make()
    assert cache.looped("wave") and not cache.looped("acid")


def test_the_loop_plays_its_frames_by_time(ctx):
    cache, _ = _cache(ctx, budget=1000)
    _until_done(cache, ["wave"], loop="wave")
    _, still0, _ = cache.picture("wave")
    assert still0 == pv.cell_uv(0)[0]
    seen = {cache.picture("wave", t=k * pv.LOOP_S / pv.LOOP_FRAMES + 1e-3)[1]
            for k in range(pv.LOOP_FRAMES)}
    assert seen == {pv.cell_uv(k)[0] for k in range(1, pv.LOOP_FRAMES + 1)}
    a, b = _cell(cache, "wave", 1), _cell(cache, "wave", pv.LOOP_FRAMES // 2)
    assert np.abs(a - b).mean() > 1                       # the wave moves


# ---------------------------------------------------------------- invalidation

def test_a_file_changed_on_disk_is_made_again_and_only_it(ctx, tmp_path):
    d = tmp_path / "fx"
    shutil.copytree(fx.FX_DIR, d)
    cache, st = _cache(ctx, d, budget=1000)
    _until_done(cache, ["wave", "acid"])
    before = _cell(cache, "wave")
    acid = _cell(cache, "acid")
    src = (d / "wave.glsl").read_text()
    # (the picture turned over: the same file, another picture)
    edited = src.replace("vec4 effect(vec2 uv) {", "vec4 effect(vec2 uv) {\n    uv = 1.0 - uv;", 1)
    assert edited != src
    (d / "wave.glsl").write_text(edited)
    st.load()                           # what the show's chain polls (ENGINEERING §15)
    ran = []
    real = fx.FxChain.run_one
    try:
        fx.FxChain.run_one = lambda self, name, *a, **k: (ran.append(name),
                                                          real(self, name, *a, **k))[1]
        _until_done(cache, ["wave", "acid"])
    finally:
        fx.FxChain.run_one = real
    assert "wave" in ran and "acid" not in ran
    assert np.abs(_cell(cache, "wave") - before).mean() > 4
    assert np.array_equal(_cell(cache, "acid"), acid)
    # a file gone: its atlas freed
    (d / "acid.glsl").unlink()
    st.load()
    _until_done(cache, ["wave"])
    assert "acid" not in cache.atlas and cache.picture("acid") is None


def test_the_shared_lib_changing_makes_every_file_again(ctx, tmp_path):
    d = tmp_path / "fx"
    shutil.copytree(fx.FX_DIR, d)
    cache, st = _cache(ctx, d, budget=1000)
    _until_done(cache, ["wave", "acid"])
    (d / fx.LIB_FILE).write_text((d / fx.LIB_FILE).read_text() + "\n// an edit\n")
    st.load()
    ran = []
    real = fx.FxChain.run_one
    try:
        fx.FxChain.run_one = lambda self, name, *a, **k: (ran.append(name),
                                                          real(self, name, *a, **k))[1]
        cache.want(["wave", "acid"])
        cache.make()
    finally:
        fx.FxChain.run_one = real
    assert {"wave", "acid", pv.CARD_EFFECT} <= set(ran)
    assert cache.made["wave"] == cache.made["acid"] == {0}


def test_a_file_that_does_not_compile_shows_the_plain_card_and_says_why(ctx, tmp_path):
    d = tmp_path / "fx"
    shutil.copytree(fx.FX_DIR, d)
    (d / "wave.glsl").write_text((d / "wave.glsl").read_text().replace(
        "vec4 effect(vec2 uv) {", "vec4 effect(vec2 uv) {\n    nonsense;", 1))
    cache, _ = _cache(ctx, d, budget=1000)
    _until_done(cache, ["wave", "testcard"])
    assert cache.failed("wave") and not cache.failed("testcard")
    assert np.abs(_cell(cache, "wave") - _cell(cache, "testcard")).mean() < 1


# ---------------------------------------------------------------- the show untouched

def test_the_outputs_are_the_same_bytes_and_the_shows_values_untouched(ctx):
    plain, shown = _renderer(ctx), _renderer(ctx)
    pv_, sv = _views(ctx), _views(ctx)
    values = {n: dict(v) for n, v in shown.fx.state.values.items()}
    phase = dict(shown.fx.state.phase)
    for k in range(4):
        t = 2.0 + k / 60
        plain.draw_outputs(S, *SIZE, 1.0, pv_, t_now=t)
        shown.effect_previews().want(["kaleido", "wave", "acid"], loop="kaleido")
        shown.draw_outputs(S, *SIZE, 1.0, sv, t_now=t)
        assert ctx.error == "GL_NO_ERROR"
        for a, b in zip(pv_, sv, strict=True):
            assert np.array_equal(_px(a.target), _px(b.target)), k
        assert plain.stats["effects"] == shown.stats["effects"]
    cache = shown.previews
    assert cache.passes and not cache.error and cache.made["kaleido"]
    assert shown.fx.state.values == values
    # the show's clocks ran on the frame's time alone, as the plain renderer's
    assert {n: shown.fx.state.phase[n] for n in phase} == {
        n: plain.fx.state.phase[n] for n in phase}


def test_a_reload_of_the_renderer_lets_the_previews_go(ctx):
    r = _renderer(ctx)
    r.effect_previews().want(["wave"])
    r.draw_outputs(S, *SIZE, 1.0, _views(ctx), t_now=2.0)
    assert r.previews.atlas
    r.on_reload()
    assert getattr(r, "previews", None) is None
    assert r.effect_previews().atlas == {}                  # made again on the next ask


# ---------------------------------------------------------------- memory

def test_every_file_fits_in_the_memory_the_plan_states(ctx):
    cache, st = _cache(ctx, budget=10_000)
    _until_done(cache, sorted(st.files))
    assert len(cache.atlas) == len(st.files) >= 27
    assert pv.ATLAS_BYTES == 960 * 540 * 4
    assert cache.bytes_kept < 64 * 2 ** 20
    assert pv.ATLAS_COLS * pv.ATLAS_ROWS == 1 + pv.LOOP_FRAMES


# ---------------------------------------------------------------- families and search

def _spec(name, label, tip="", order=50, family=""):
    return fx.parse(name, f"// @label {label}\n// @order {order}\n"
                    + (f"// @family {family}\n" if family else "")
                    + (f"// @tip {tip}\n" if tip else "")
                    + "vec4 effect(vec2 uv) { return src(uv); }\n")


def test_a_files_family_is_its_at_family_else_its_order_band():
    assert _spec("a", "A", order=5).family == ""
    assert pv.family_of(_spec("a", "A", order=5)) == "generators"
    assert pv.family_of(_spec("a", "A", order=27)) == "distort"
    assert pv.family_of(_spec("a", "A", order=95)) == "colour"
    one = _spec("a", "A", order=27, family="Flow")
    assert one.family == "flow" and pv.family_of(one) == "flow"
    # (a family declares nothing: no param re-declared when it changes)
    assert one.signature() == _spec("a", "A", order=27).signature()


def test_the_groups_come_from_the_files_in_family_order():
    specs = [_spec("w", "Wave", order=27), _spec("p", "Plasma", order=5),
             _spec("g", "Grain", order=93), _spec("k", "Kaleidoscope", order=15),
             _spec("x", "Xeno", order=50, family="weird")]
    got = [(f, [s.name for s in g]) for f, g in pv.families(specs)]
    assert got == [("generators", ["p"]), ("distort", ["k", "w"]), ("colour", ["g"]),
                   ("weird", ["x"])]


def test_every_shipped_file_has_a_family_and_the_test_card_is_a_generator():
    st = FxState()
    fams = {n: pv.family_of(s) for n, s in st.files.items()}
    assert pv.OTHER not in fams.values()
    assert fams["testcard"] == fams["plasma"] == "generators"
    assert fams["wave"] == "distort"


@pytest.mark.parametrize(("query", "want"), [
    ("", {"w", "wt", "g", "k"}),
    ("wave", {"w", "wt"}),
    ("WAVE", {"w", "wt"}),
    ("table", {"wt"}),
    ("film", {"g"}),                    # a word of the tip
    ("mirror segments", {"k"}),         # every word, anywhere
    ("mirror wave", set()),
    ("colour", {"g"}),                  # the family's word
])
def test_the_search_filters_on_label_and_tip(query, want):
    specs = [_spec("w", "Wave", "Ripples run across the frame.", order=27),
             _spec("wt", "Wave Table", "Shapes from a table.", order=24),
             _spec("g", "Grain", "Film grain over the picture.", order=93),
             _spec("k", "Kaleidoscope", "Mirror segments about the centre.", order=15)]
    assert {s.name for s in specs if pv.matches(s, query)} == want
    assert {s.name for _, g in pv.families(specs, query) for s in g} == want


def test_a_no_op_mix_is_shown_at_full_mix():
    st = FxState()
    assert st.files["palette"].mix == 0.0
    assert pv.preview_values(st.files["palette"])["mix"] == 1.0
    assert pv.preview_values(st.files["wave"])["mix"] == st.files["wave"].mix


# ---------------------------------------------------------------- the aux

def test_a_file_reads_aux_when_its_code_calls_it_and_not_in_a_comment():
    assert fx.reads_aux("vec4 effect(vec2 uv) { return aux(uv); }")
    assert fx.reads_aux("vec4 effect(vec2 uv) { float l = aux_luma (uv); return src(uv); }")
    assert not fx.reads_aux("// the aux(uv) is not read\nvec4 effect(vec2 uv) { return src(uv); }")
    assert not fx.reads_aux("/* aux(uv) */ vec4 effect(vec2 uv) { return src(uv); }")
    assert not fx.reads_aux("vec4 effect(vec2 uv) { float auxiliary(uv); return src(uv); }")


def test_on_this_build_the_files_that_read_their_aux():
    """The finding the plan records (2026-11-19): every effect node has an aux
    port, and two files read it. A file that starts reading one is found by
    `fx.reads_aux`; this list is the record, to be changed with the file
    (plan 66: Time Displace reads its aux as a field, the third)."""
    st = FxState()
    assert sorted(n for n, s in st.files.items() if s.aux) == ["blend", "displace", "timedisplace"]
    assert st.files["blend"].signature() == fx.parse("blend", st.files["blend"].source).signature()


def test_an_aux_effects_preview_has_the_known_aux_and_shows_it(ctx):
    cache, _ = _cache(ctx, budget=1000)
    _until_done(cache, ["blend", "displace", "testcard", "wave"])
    card = _cell(cache, "testcard")
    # blend lays the aux disc over the card: its warm centre in the middle
    blend = _cell(cache, "blend")
    h, w = blend.shape[:2]
    r, _, b = blend[h // 2, w // 2 + 8, :3]
    assert r > 180 and r > b + 80
    # displace bends the card's lines inside the disc
    assert np.abs(_cell(cache, "displace") - card).mean() > 4
    assert cache._aux is not None
