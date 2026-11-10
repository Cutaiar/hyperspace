"""The light effects: `prism`, `oilslick`, `grain` and `bloom` (shaders/fx/).

Each is one file in the folder, so what is held here is what each one
*does* — the invariants a knob can break without the compile failing:

- **prism** resamples the frame once per wavelength. At Amount 0 and Tilt 0
  every tap lands on the same pixel, so the picture has to come back
  unchanged: the spectral weights are normalised per channel, and a
  rounding error there would tint the whole frame.
- **oilslick** tints the light that comes *through* the film, so a black
  pixel stays black (the sheen it throws back is Glow's, and Ground's).
- **grain** adds noise and may crush the levels; at Amount 0 with Steps 0
  it is the picture byte for byte.
- **bloom** spreads what is over the threshold and adds it back, so it only
  ever lights a pixel and never takes light away, and nothing under the
  threshold spills at all.

The passes run on a see-through ground (`opaque=0`), so what is asserted
is what the alpha tail (`fx.FS_TAIL`) leaves: alpha lifted to cover the
colour and no further.
"""

import numpy as np
import pytest

from hyperspace.fx import FX_DIR, FxChain, FxState, parse

W, H = 64, 48

moderngl = pytest.importorskip("moderngl")


# ---------------------------------------------------------------- the pictures

def flat(rgb, a=255) -> np.ndarray:
    pic = np.zeros((H, W, 4), np.uint8)
    pic[...] = (*rgb, a)
    return pic


def white_line() -> np.ndarray:
    """A black frame with one white column down the middle, opaque."""
    pic = flat((0, 0, 0))
    pic[:, W // 2, :3] = 255
    return pic


def run(ctx, name: str, picture: np.ndarray, t: float = 0.0, **values) -> np.ndarray:
    """One pass of `name` over `picture` (H × W × 4 uint8, premultiplied) on
    a see-through ground; the pixels the tail leaves."""
    st = FxState()
    st.values[name].update(on=True, **values)
    chain = FxChain(ctx, st)
    src = ctx.texture((W, H), 4, np.ascontiguousarray(picture).tobytes())
    out = ctx.framebuffer(color_attachments=[ctx.texture((W, H), 4)])
    chain.run_one(name, src, out, t, opaque=0)
    assert ctx.error == "GL_NO_ERROR"
    px = np.frombuffer(out.read(components=4), dtype=np.uint8).reshape(H, W, 4).copy()
    for o in (src, out):
        o.release()
    return px


def frames(ctx, name: str, picture: np.ndarray, times, **values) -> list[np.ndarray]:
    """The same pass at each of `times` on one chain, so the clocks run: the
    chain integrates by the gap since the last call (`FxState.advance_to`),
    and a pass on a fresh chain always sees phase 0."""
    st = FxState()
    st.values[name].update(on=True, **values)
    chain = FxChain(ctx, st)
    src = ctx.texture((W, H), 4, np.ascontiguousarray(picture).tobytes())
    out = ctx.framebuffer(color_attachments=[ctx.texture((W, H), 4)])
    shots = []
    for t in times:
        chain.run_one(name, src, out, t, opaque=0)
        assert ctx.error == "GL_NO_ERROR"
        shots.append(np.frombuffer(out.read(components=4), dtype=np.uint8)
                     .reshape(H, W, 4).copy())
    for o in (src, out):
        o.release()
    return shots


def chroma(px: np.ndarray) -> np.ndarray:
    """How far each pixel is from grey, 0 … 255."""
    rgb = px[..., :3].astype(int)
    return rgb.max(axis=-1) - rgb.min(axis=-1)


# ---------------------------------------------------------------- what they declare

def test_prism_declares_its_params():
    spec = parse("prism", (FX_DIR / "prism.glsl").read_text())
    assert spec.label == "Prism" and spec.blend == 0 and spec.mix == 1.0   # @blend mix
    got = {p.key: (p.lo, p.hi, p.default, p.integer) for p in spec.params}
    assert got == {"amount": (0.0, 0.4, 0.02, False), "rim": (0.0, 3.0, 1.0, False),
                   "tilt": (0.0, 24.0, 0.0, False), "fringe": (0.0, 2.0, 0.5, False),
                   "cx": (-1.0, 1.0, 0.0, False), "cy": (-1.0, 1.0, 0.0, False),
                   "taps": (3.0, 32.0, 16.0, True)}
    amount, = (p for p in spec.params if p.key == "amount")
    assert amount.amount and not spec.clocks
    st = FxState()
    assert "prism" in st.specs and st.errors == {} and st.values["prism"]["on"] is False


def test_oilslick_declares_its_params_and_integrates_its_drift():
    spec = parse("oilslick", (FX_DIR / "oilslick.glsl").read_text())
    assert spec.label == "Oil slick" and spec.blend == 0                   # @blend mix
    got = {p.key: (p.lo, p.hi, p.default) for p in spec.params}
    assert got == {"amount": (0.0, 1.0, 0.8), "glow": (0.0, 2.0, 0.35),
                   "halo": (0.0, 48.0, 18.0), "scale": (0.5, 24.0, 3.0),
                   "bands": (0.25, 12.0, 1.5), "rings": (0.0, 8.0, 1.5),
                   "drift": (0.0, 4.0, 1.0), "ground": (0.0, 1.0, 0.0)}
    # the drift is integrated here, never multiplied into the clock (K2): the
    # cells a second are drift × scale, so a Scale step re-zooms and slides nothing
    clock, = spec.clocks
    assert clock.uniform == "u_drift_t" and clock.rate == "drift*scale"
    assert clock.factors == ("drift", "scale") and clock.period is None
    assert FxState().errors == {}


def test_grain_declares_its_params():
    spec = parse("grain", (FX_DIR / "grain.glsl").read_text())
    assert spec.label == "Grain" and spec.blend == 0 and spec.speed == 1.0
    got = {p.key: (p.lo, p.hi, p.default, p.integer) for p in spec.params}
    assert got == {"amount": (0.0, 1.0, 0.15, False), "size": (0.5, 8.0, 1.0, False),
                   "tone": (0.0, 1.0, 0.6, False), "colour": (0.0, 1.0, 0.25, False),
                   "ground": (0.0, 1.0, 0.0, False), "steps": (0.0, 32.0, 0.0, True),
                   "dither": (0.0, 1.0, 1.0, False)}
    assert FxState().errors == {}


def test_palette_is_still_the_last_order_of_the_three_added_here():
    """`// @order` is only what an old loadable patch's absent order means
    (graphmigrate), but `tests/test_fx_palette.py` holds palette as the
    highest: a new file takes a free number below it."""
    st = FxState()
    orders = {n: s.order for n, s in st.specs.items()}
    for name in ("prism", "oilslick", "grain", "bloom"):
        assert orders[name] < orders["palette"], name
    assert len(set(orders.values())) == len(orders), "two files took one order"


# ---------------------------------------------------------------- prism

@pytest.mark.parametrize("rgb", [(0, 0, 0), (255, 255, 255), (200, 90, 40)])
def test_prism_with_no_split_is_the_picture_it_was_given(ctx, rgb):
    """Amount 0, Tilt 0: every wavelength samples the same pixel, so the
    weights summed per channel have to come back to 1 — a rounding error
    there would tint every frame. Fringe is up too: it deepens the colour
    the split made, and with no split there is none to deepen, so a frame
    that already has colour of its own keeps it."""
    pic = flat(rgb)
    px = run(ctx, "prism", pic, amount=0.0, tilt=0.0, fringe=2.0)
    assert np.abs(px[..., :3].astype(int) - pic[..., :3]).max() <= 1, px[0, 0]


def test_prism_splits_a_white_line_red_outward_and_blue_inward(ctx):
    """Lateral chromatic aberration: the long wavelengths land further from
    the centre than the short ones, so the fringe left of a line left of
    centre is blue and the fringe on its right (away from the middle) is red."""
    pic = flat((0, 0, 0))
    pic[:, 16, :3] = 255                       # a line left of the centre column
    px = run(ctx, "prism", pic, amount=0.08, rim=0.0, fringe=0.0, taps=24)
    row = px[H // 2]
    left, right = row[10:16, :3].astype(int), row[17:23, :3].astype(int)
    assert left[:, 2].sum() > left[:, 0].sum() * 1.5, "the inward fringe is not blue"
    assert right[:, 0].sum() > right[:, 2].sum() * 1.5, "the outward fringe is not red"


def test_prisms_rim_decides_where_the_split_happens(ctx):
    """Rim 0 splits the whole frame the same; Rim 3 leaves the middle alone
    and keeps the split for the outside."""
    pic = white_line()
    flatly = run(ctx, "prism", pic, amount=0.1, rim=0.0, taps=24)
    rimmed = run(ctx, "prism", pic, amount=0.1, rim=3.0, taps=24)
    near, far = slice(H // 2 - 3, H // 2 + 3), slice(0, 6)
    assert chroma(rimmed[near]).sum() < chroma(flatly[near]).sum() * 0.5
    assert chroma(rimmed[far]).sum() > chroma(rimmed[near]).sum()


def test_prisms_fringe_only_takes_the_colour_further_out(ctx):
    pic = white_line()
    low = run(ctx, "prism", pic, amount=0.06, fringe=0.0)
    high = run(ctx, "prism", pic, amount=0.06, fringe=2.0)
    assert chroma(high).sum() > chroma(low).sum() * 1.3


def test_prisms_tilt_splits_with_no_amount_at_all(ctx):
    """A prism in the path: a straight split that does not grow from a centre."""
    pic = white_line()
    assert chroma(run(ctx, "prism", pic, amount=0.0, tilt=12.0)).sum() > 0
    assert not chroma(run(ctx, "prism", pic, amount=0.0, tilt=0.0)).any()


# ---------------------------------------------------------------- oil slick

def test_the_slick_leaves_black_black(ctx):
    """The film tints the light through it. With no Glow and no Ground
    nothing is thrown back, so an empty frame comes out empty — a slick
    never lights a pixel the picture did not."""
    px = run(ctx, "oilslick", flat((0, 0, 0), a=0), glow=0.0, ground=0.0, amount=1.0)
    assert not px.any(), px.max()


def test_the_slick_with_nothing_turned_up_is_the_picture_it_was_given(ctx):
    pic = flat((180, 180, 180))
    px = run(ctx, "oilslick", pic, amount=0.0, glow=0.0, ground=0.0)
    assert np.abs(px[..., :3].astype(int) - pic[..., :3]).max() <= 1


def test_the_slick_tints_a_white_frame_in_more_than_one_hue(ctx):
    """A thickness that swings over the frame is a thickness that walks the
    spectrum: the film's colour here is not the film's colour there."""
    px = run(ctx, "oilslick", flat((200, 200, 200)), amount=1.0, glow=0.0, bands=3.0)
    assert chroma(px).max() > 20, chroma(px).max()
    rgb = px[..., :3].astype(int)
    hue = np.argmax(rgb, axis=-1)
    assert len(np.unique(hue)) > 1, "one colour over the whole frame: not a film"


def test_the_slicks_glow_reaches_past_the_line_and_ground_covers_the_frame(ctx):
    pic = white_line()
    tight = run(ctx, "oilslick", pic, amount=0.0, glow=1.0, halo=0.0)
    wide = run(ctx, "oilslick", pic, amount=0.0, glow=1.0, halo=20.0)
    far = np.s_[:, :W // 2 - 8, :3]        # the ground is opaque black: colour only
    assert not tight[far].any(), "the haze reached with no halo"
    assert wide[far].any(), "the haze did not reach"
    # Ground lays the film over the empty frame. Not every pixel of it is
    # lit: where the three wavelengths all come back through, the film
    # throws nothing back — a real one goes black there too, just before it
    # pops — so what is held is that it covers the frame, not every pixel.
    everywhere = run(ctx, "oilslick", flat((0, 0, 0), a=0), glow=1.0, ground=1.0, halo=0.0)
    assert (everywhere[..., 3] > 0).mean() > 0.9, "ground left the frame empty"


# ---------------------------------------------------------------- grain

def test_grain_with_nothing_turned_up_is_the_picture_it_was_given(ctx):
    pic = flat((120, 130, 140))
    px = run(ctx, "grain", pic, amount=0.0, steps=0)
    assert np.array_equal(px[..., :3], pic[..., :3])


def test_grain_stays_off_the_see_through_parts_until_ground(ctx):
    """Premultiplied: a pixel the picture never covered is not the grain's
    to light, unless Ground says it is."""
    empty = flat((0, 0, 0), a=0)
    assert not run(ctx, "grain", empty, amount=1.0, ground=0.0).any()
    assert run(ctx, "grain", empty, amount=1.0, ground=1.0).any()


def test_grains_tone_keeps_black_and_white_and_works_the_midtones(ctx):
    """Film grain lives in the midtones. At Tone 1 a white frame comes back
    white and a mid-grey one does not."""
    white = flat((255, 255, 255))
    mid = flat((128, 128, 128))
    assert np.array_equal(run(ctx, "grain", white, amount=1.0, tone=1.0)[..., :3],
                          white[..., :3])
    assert run(ctx, "grain", mid, amount=0.5, tone=1.0)[..., :3].std() > 2
    # at Tone 0 it is flat video noise: the white frame is grained too
    assert run(ctx, "grain", white, amount=0.5, tone=0.0)[..., :3].std() > 2


def test_grains_colour_decides_whether_the_three_channels_share_their_noise(ctx):
    mid = flat((128, 128, 128))
    grey = run(ctx, "grain", mid, amount=0.6, colour=0.0, tone=0.0)
    assert chroma(grey).max() <= 1, "grey grain coloured the frame"
    assert chroma(run(ctx, "grain", mid, amount=0.6, colour=1.0, tone=0.0)).max() > 4


def test_grains_steps_crush_the_levels_and_the_dither_breaks_the_bands(ctx):
    """A ramp through Steps 4 with no dither holds four values a channel;
    the dither trades those hard steps for a 4-px pattern, so the ramp comes
    back with more values than levels and no more than the levels in any
    one row of a tile."""
    ramp = np.zeros((H, W, 4), np.uint8)
    ramp[..., 3] = 255
    ramp[..., :3] = (np.arange(W) * 255 // (W - 1)).astype(np.uint8)[None, :, None]
    hard = run(ctx, "grain", ramp, amount=0.0, steps=4, dither=0.0)
    assert len(np.unique(hard[..., 0])) == 4, np.unique(hard[..., 0])
    dithered = run(ctx, "grain", ramp, amount=0.0, steps=4, dither=1.0)
    assert len(np.unique(dithered[..., 0])) == 4, "the dither invented a level"
    # the same column is not the same value down the frame any more: the
    # 4 × 4 pattern decides which side of a step each pixel falls
    assert (dithered[:, :, 0].std(axis=0) > 0).any(), "the dither changed nothing"


def test_grains_shutter_stops_with_the_speed(ctx):
    """The grain is redrawn off `u_phase`, which the chain integrates at the
    speed fader's rate: at speed 0 the phase never moves, so the field is the
    same field however long the pass runs."""
    mid = flat((128, 128, 128))
    still = frames(ctx, "grain", mid, [0.0, 0.2, 0.4], amount=0.6, speed=0.0)
    assert np.array_equal(still[0], still[-1])
    moved = frames(ctx, "grain", mid, [0.0, 0.2, 0.4], amount=0.6, speed=1.0)
    assert np.array_equal(moved[0], still[0]), "the first frame is not the same field"
    assert not np.array_equal(moved[0], moved[-1]), "the grain never moved"


# ---------------------------------------------------------------- bloom

def test_bloom_declares_its_params():
    spec = parse("bloom", (FX_DIR / "bloom.glsl").read_text())
    assert spec.label == "Bloom" and spec.blend == 1                  # @blend add
    got = {p.key: (p.lo, p.hi, p.default, p.integer) for p in spec.params}
    assert got == {"amount": (0.0, 4.0, 0.8, False), "threshold": (0.0, 1.0, 0.4, False),
                   "knee": (0.0, 1.0, 0.3, False), "radius": (2.0, 160.0, 20.0, False),
                   "falloff": (0.5, 4.0, 1.8, False), "taps": (8.0, 96.0, 40.0, True)}
    # it reads no clock: the kernel is a still disc, and the dither in it is
    # fixed per pixel, so nothing here boils
    assert not spec.clocks and "u_phase" not in spec.source
    assert FxState().errors == {}


def test_bloom_spills_nothing_that_is_under_the_threshold(ctx):
    """A frame no brighter than the threshold has no light to give, so the
    pass adds nothing and what comes back is what went in — and a frame of
    nothing stays nothing, Amount as high as it goes."""
    dim = flat((90, 90, 90))                       # 0.35, under a 0.6 threshold
    assert np.array_equal(run(ctx, "bloom", dim, threshold=0.6, amount=4.0)[..., :3],
                          dim[..., :3])
    assert not run(ctx, "bloom", flat((0, 0, 0), a=0), amount=4.0).any()


def test_bloom_only_ever_adds_light(ctx):
    """`@blend add`: every channel of every pixel comes back at least what it
    was. A bloom that darkened anything would be a bug in the blend."""
    pic = white_line()
    px = run(ctx, "bloom", pic, amount=2.0)
    assert (px[..., :3].astype(int) >= pic[..., :3].astype(int)).all()


def test_blooms_radius_is_how_far_the_light_reaches(ctx):
    """The halo off a line, measured as the last column that lit up: a wider
    radius reaches further, and it stops where the radius says."""
    pic = white_line()

    def reach_px(radius):
        px = run(ctx, "bloom", pic, amount=4.0, radius=radius, taps=96, falloff=0.5)
        lit = np.nonzero(px[H // 2 + 3, :, :3].sum(axis=-1) > 0)[0]
        return W // 2 - lit.min()

    near, far = reach_px(6.0), reach_px(24.0)
    assert near < far, (near, far)
    assert near <= 8 and far <= 28, (near, far)   # neither runs past its radius


def test_blooms_falloff_decides_how_much_of_the_halo_is_out_at_the_edge(ctx):
    """Low Falloff is a veil that keeps its light out to the radius; high is a
    rim that has spent it by then. Measured as the share of the halo's light
    in the outer half of its reach."""
    pic = white_line()

    def outer_share(falloff):
        px = run(ctx, "bloom", pic, amount=3.0, radius=24.0, taps=96, falloff=falloff)
        row = px[H // 2 + 3, :, :3].astype(float).sum(axis=-1)
        band = row[W // 2 - 24:W // 2 - 2]
        return band[:11].sum() / max(band.sum(), 1e-6)   # the outer half of the band

    assert outer_share(0.5) > outer_share(4.0)


def test_blooms_knee_brings_the_spill_in_over_a_range(ctx):
    """At a hard knee a frame just under the threshold gives nothing and one
    just over gives everything; a wide knee has the one in between give some."""
    just_over = flat((140, 140, 140))              # 0.55, over a 0.5 threshold
    hard = run(ctx, "bloom", just_over, threshold=0.5, knee=0.0, amount=1.0)
    soft = run(ctx, "bloom", just_over, threshold=0.5, knee=0.5, amount=1.0)
    assert hard[..., :3].mean() > soft[..., :3].mean() > 0
