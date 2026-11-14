"""The distortion effects: `shake`, `wave` and `blocks` (shaders/fx/), and
the two helpers in `_lib.glsl` they are built on (`wave`, `pushed`).

Each is a field of offsets — where every pixel reads the frame from — so
what is held here is what a field can get wrong without the compile
failing:

- at Amount 0 every one of them, in every mode, is the picture again: a
  lane on Amount (a bass band, a hand) then fades the effect in from
  nothing, which is what they are for;
- a flat frame stays flat whatever the field (it only moves pixels);
- the push goes where the knobs say: a slide moves a line sideways and a
  squeeze along it does not; a block shifts by Amount cells and a swap by
  whole cells; a shake's orbit starts a throw to the side;
- Split parts the colours only where the field moves the picture.
"""

import numpy as np
import pytest

from hyperspace.fx import FX_DIR, FxChain, FxState, parse

W, H = 64, 48

moderngl = pytest.importorskip("moderngl")

NAMES = ("shake", "wave", "blocks")


def flat(rgb, a=255) -> np.ndarray:
    pic = np.zeros((H, W, 4), np.uint8)
    pic[...] = (*rgb, a)
    return pic


def white_line() -> np.ndarray:
    """A black frame with one white column down the middle, opaque."""
    pic = flat((0, 0, 0))
    pic[:, W // 2, :3] = 255
    return pic


def speckle() -> np.ndarray:
    rng = np.random.default_rng(7)
    pic = rng.integers(0, 256, (H, W, 4), dtype=np.uint8)
    pic[..., 3] = 255
    return pic


def frames(ctx, name: str, picture: np.ndarray, times, **values) -> list[np.ndarray]:
    """One pass of `name` at each of `times` on one chain (the clocks run
    by the gap between calls; the first call sees phase 0)."""
    st = FxState()
    st.values[name].update(on=True, **values)
    chain = FxChain(ctx, st)
    src = ctx.texture((W, H), 4, np.ascontiguousarray(picture).tobytes())
    out = ctx.framebuffer(color_attachments=[ctx.texture((W, H), 4)])
    shots = []
    for t in times:
        chain.run_one(name, src, out, t, opaque=1)
        assert ctx.error == "GL_NO_ERROR"
        shots.append(np.frombuffer(out.read(components=4), dtype=np.uint8)
                     .reshape(H, W, 4).copy())
    assert st.errors == {}
    for o in (src, out):
        o.release()
    return shots


def run(ctx, name: str, picture: np.ndarray, **values) -> np.ndarray:
    return frames(ctx, name, picture, [0.0], **values)[0]


def column(px: np.ndarray) -> np.ndarray:
    """Per row, where the white line is (its brightest pixel's x)."""
    return px[..., 1].argmax(axis=1)


def chroma(px: np.ndarray) -> np.ndarray:
    rgb = px[..., :3].astype(int)
    return rgb.max(axis=-1) - rgb.min(axis=-1)


def choice(name: str, key: str, word: str) -> int:
    spec = parse(name, (FX_DIR / f"{name}.glsl").read_text())
    p, = (p for p in spec.params if p.key == key)
    return p.choices.index(word)


def modes(name: str) -> list[dict]:
    """Every value of every choice the effect has, one at a time."""
    spec = parse(name, (FX_DIR / f"{name}.glsl").read_text())
    return [{p.key: k} for p in spec.params if p.choices for k in range(len(p.choices))]


# ---------------------------------------------------------------- what they declare

@pytest.mark.parametrize("name,clock,rate", [("shake", "u_shake_t", "rate"),
                                             ("wave", "u_drift_t", "drift"),
                                             ("blocks", "u_drift_t", "drift")])
def test_each_declares_an_amount_and_integrates_its_rate(name, clock, rate):
    spec = parse(name, (FX_DIR / f"{name}.glsl").read_text())
    amount, = (p for p in spec.params if p.key == "amount")
    assert amount.amount and amount.lo == 0.0
    # the rate is a clock of the host's, never time × a knob (K2), and wraps
    # where `wave`'s noise repeats
    c, = spec.clocks
    assert (c.uniform, c.rate, c.period) == (clock, rate, 4096.0)
    assert {"split"} <= {p.key for p in spec.params}
    assert FxState().errors == {}


def test_the_choices_are_the_ones_the_tips_name():
    got = {(n, p.key): p.choices for n in NAMES
           for p in parse(n, (FX_DIR / f"{n}.glsl").read_text()).params if p.choices}
    shapes = ("sine", "triangle", "square", "saw", "noise")     # `wave` in _lib.glsl, in order
    assert got == {("shake", "motion"): ("buzz", "orbit", "punch", "jolt"),
                   ("wave", "along"): ("line", "rings", "spokes"),
                   ("wave", "push"): ("slide", "squeeze"),
                   ("wave", "shape"): shapes,
                   ("blocks", "action"): ("shift", "zoom", "stretch", "turn", "bulge", "swap"),
                   ("blocks", "rule"): ("rows", "columns", "diagonal", "rings", "random"),
                   ("blocks", "shape"): shapes}


# ---------------------------------------------------------------- nothing at 0, flat stays flat

@pytest.mark.parametrize("name", NAMES)
def test_amount_zero_is_the_picture_in_every_mode(ctx, name):
    pic = speckle()
    for mode in [{}, *modes(name)]:
        for extra in ({}, {"split": 1.0}, {"smear": 1.0} if name == "shake" else {"split": 0.5}):
            got = frames(ctx, name, pic, [0.0, 0.31], amount=0.0, **mode, **extra)
            for px in got:
                assert np.abs(px.astype(int) - pic).max() <= 1, (name, mode, extra)


@pytest.mark.parametrize("name", NAMES)
def test_a_flat_frame_stays_flat(ctx, name):
    pic = flat((40, 120, 200))
    hi = {p.key: p.hi for p in parse(name, (FX_DIR / f"{name}.glsl").read_text()).params
          if p.key == "amount"}
    for mode in [{}, *modes(name)]:
        for px in frames(ctx, name, pic, [0.0, 0.31], split=1.0, **hi, **mode):
            assert np.abs(px.astype(int) - pic).max() <= 1, (name, mode)


# ---------------------------------------------------------------- shake

def test_an_orbit_starts_a_throw_to_the_side(ctx):
    """At phase 0 an orbit reads Amount frame heights to the right, so the
    line lands that far to the left: 0.125 × 48 = 6 px."""
    px = run(ctx, "shake", white_line(), amount=0.125, motion=choice("shake", "motion", "orbit"))
    assert set(column(px)) == {W // 2 - 6}


def test_a_buzz_moves_along_its_angle_and_comes_back(ctx):
    line = white_line()
    # rate 1: a quarter of a second in, the sine is at its crest
    across = frames(ctx, "shake", line, [0.0, 0.125, 0.25], amount=0.125, rate=1.0, angle=0.0)
    assert set(column(across[0])) == {W // 2}            # phase 0: at rest
    assert set(column(across[2])) == {W // 2 - 6}        # the crest: the whole throw
    # shaken along the line itself, a vertical line does not move
    up = frames(ctx, "shake", line, [0.0, 0.125, 0.25], amount=0.125, rate=1.0,
                angle=np.pi / 2)
    assert set(column(up[2])) == {W // 2}


def test_split_fringes_a_shake_and_smear_spreads_it(ctx):
    line = white_line()
    orbit = choice("shake", "motion", "orbit")
    plain = run(ctx, "shake", line, amount=0.125, motion=orbit)
    assert chroma(plain).max() == 0
    split = run(ctx, "shake", line, amount=0.125, motion=orbit, split=1.0)
    assert chroma(split).max() > 200                     # three lines, one a colour
    # the open shutter spreads the line's light over more pixels, no brighter
    smear = run(ctx, "shake", line, amount=0.125, motion=orbit, smear=1.0)
    lit = lambda px: int((px[H // 2, :, 1] > 8).sum())
    assert lit(smear) > lit(plain) and smear[..., 1].max() < plain[..., 1].max()


# ---------------------------------------------------------------- wave

def test_a_slide_bends_a_line_and_a_squeeze_along_it_does_not(ctx):
    """The default wave travels up the frame. Slide pushes sideways to
    that, so each row of a vertical line lands somewhere else; squeeze
    pushes up and down, along the line, and it stays where it is."""
    line = white_line()
    slide = run(ctx, "wave", line, amount=0.125, waves=1.0)
    cols = column(slide)
    assert cols.max() - cols.min() >= 10                 # ±6 px, crest to trough
    assert abs(int(cols.max()) + int(cols.min()) - W) <= 2   # and about the line
    squeeze = run(ctx, "wave", line, amount=0.125, waves=1.0,
                  push=choice("wave", "push", "squeeze"))
    assert set(column(squeeze)) == {W // 2}


def test_a_square_wave_has_two_levels_and_steps_flatten_a_sine(ctx):
    line = white_line()
    square = run(ctx, "wave", line, amount=0.125, waves=1.0,
                 shape=choice("wave", "shape", "square"))
    assert set(column(square)) == {W // 2 - 6, W // 2 + 6}
    stepped = run(ctx, "wave", line, amount=0.125, waves=1.0, steps=1)
    assert set(column(stepped)) == {W // 2 - 6, W // 2, W // 2 + 6}


def test_rings_squeeze_is_the_same_all_the_way_round(ctx):
    """Counted out from the centre and pushed along the radius, the field
    has the frame's own symmetries: a picture with them keeps them."""
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.hypot(xx - (W - 1) / 2, yy - (H - 1) / 2)
    pic = flat((0, 0, 0))
    pic[..., :3] = (np.clip(255 - r * 8, 0, 255)).astype(np.uint8)[..., None]
    px = run(ctx, "wave", pic, amount=0.1, waves=3.0, along=choice("wave", "along", "rings"),
             push=choice("wave", "push", "squeeze")).astype(int)
    assert np.abs(px - pic).max() > 20                              # it did something
    assert np.abs(px - px[::-1]).max() <= 2 and np.abs(px - px[:, ::-1]).max() <= 2


@pytest.mark.parametrize("shape", ["sine", "noise"])
def test_spokes_have_no_seam_where_the_angle_wraps(ctx, shape):
    """Counted round the centre, the wave meets itself where the angle wraps
    (the −x axis): noise repeats every turn there, as a sine does. A smooth
    picture pushed by it is as smooth across that line as across the +x one."""
    yy, xx = np.mgrid[0:H, 0:W]
    pic = flat((0, 0, 0))
    pic[..., 0] = xx * 255 // (W - 1)
    pic[..., 1] = yy * 255 // (H - 1)
    px = run(ctx, "wave", pic, amount=0.2, waves=5.0, drift=0.0,
             along=choice("wave", "along", "spokes"), shape=choice("wave", "shape", shape))
    px = px.astype(int)
    assert np.abs(px - pic).max() > 20
    jump = np.abs(px[H // 2] - px[H // 2 - 1])[:, :2].max(axis=-1)   # across the x axis
    left, right = jump[4:W // 2 - 4], jump[W // 2 + 4:W - 4]
    assert left.max() <= right.max() + 12, (left.max(), right.max())


def test_the_wave_drifts_and_split_follows_the_push(ctx):
    line = white_line()
    a, b = frames(ctx, "wave", line, [0.0, 0.25], amount=0.125, waves=1.0, drift=1.0)
    assert (column(a) != column(b)).any()
    assert chroma(a).max() == 0
    # the colours part where the wave moves the picture, and only there: a
    # squeeze along the line moves none of it
    split = run(ctx, "wave", line, amount=0.125, waves=1.0, split=1.0)
    assert chroma(split).max(axis=1).min() >= 200
    along = run(ctx, "wave", line, amount=0.125, waves=1.0, split=1.0,
                push=choice("wave", "push", "squeeze"))
    assert chroma(along).max() == 0


# ---------------------------------------------------------------- blocks

def test_rows_shift_every_other_row_the_other_way(ctx):
    """Rule rows, Spread ½, a still sine: a row of cells sits on the crest
    and the next on the trough, so an 8-px cell at Amount 0.5 slides 4 px
    one way, then 4 px the other, 8 rows of pixels at a time."""
    px = run(ctx, "blocks", white_line(), amount=0.5, cell=8.0, drift=0.0,
             rule=choice("blocks", "rule", "rows"))
    cols = column(px)
    assert set(cols) == {W // 2 - 4, W // 2 + 4}
    runs = np.diff(np.flatnonzero(np.diff(cols) != 0))
    assert set(runs) == {8}


def test_a_group_hands_one_number_to_a_block_of_cells(ctx):
    px = run(ctx, "blocks", white_line(), amount=0.5, cell=4.0, group=2, drift=0.0,
             rule=choice("blocks", "rule", "rows"))
    cols = column(px)
    assert set(cols) == {W // 2 - 2, W // 2 + 2}         # half a 4-px cell
    assert set(np.diff(np.flatnonzero(np.diff(cols) != 0))) == {8}   # in 2-cell rows


def cell_ids() -> tuple[np.ndarray, np.ndarray]:
    """Each pixel's cell in an 8-px grid, as the shader counts them: a cell
    sits on the frame's centre, so cell 0 is x 28 … 35 and y 20 … 27."""
    yy, xx = np.mgrid[0:H, 0:W]
    return (np.floor((xx + 0.5 - W / 2) / 8 + 0.5).astype(int),
            np.floor((yy + 0.5 - H / 2) / 8 + 0.5).astype(int))


def cells() -> np.ndarray:
    """Every 8-px cell its own flat colour."""
    cx, cy = cell_ids()
    pic = flat((0, 0, 0))
    pic[..., 0] = (cx + 8) * 13
    pic[..., 1] = (cy + 8) * 17
    return pic


@pytest.mark.parametrize("rule", ["rows", "columns", "random"])
@pytest.mark.parametrize("angle", [0.0, np.pi / 2])
def test_a_swap_shows_every_cell_once(ctx, rule, angle):
    """Blocks pair off (cells 2k and 2k + 1 along the angle's nearer axis)
    and a pair shares one number, so both agree to trade: whatever the rule,
    the output is the input's cells rearranged — each whole, each exactly
    once — and a cell that moved is where its partner was."""
    pic = cells()
    swap = choice("blocks", "action", "swap")
    px = run(ctx, "blocks", pic, amount=1.0, cell=8.0, drift=0.0, angle=angle, spread=0.37,
             action=swap, rule=choice("blocks", "rule", rule))
    cx, cy = cell_ids()
    along = cx if angle == 0.0 else cy
    # the whole cells whose partner is whole too (the frame's edge cuts the rest)
    whole = (cx >= -3) & (cx <= 3) & (cy >= -2) & (cy <= 2)
    whole &= (along >= -2) & (along <= (3 if angle == 0.0 else 1))
    partner = np.where(along % 2 == 0, 8, -8)
    there = np.roll(pic, -8, axis=1 if angle == 0.0 else 0)
    back = np.roll(pic, 8, axis=1 if angle == 0.0 else 0)
    traded = np.where((partner == 8)[..., None], there, back)
    kept = (px == pic).all(-1)
    moved = (px == traded).all(-1)
    assert (kept | moved)[whole].all()
    assert moved[whole].any()
    # a cell moves whole, and with its partner: the pair's 16 × 8 px agree
    pair = (np.floor(along / 2), np.where(angle == 0.0, cy, cx))
    for a in np.unique(pair[0][whole]):
        for b in np.unique(pair[1][whole]):
            m = whole & (pair[0] == a) & (pair[1] == b)
            assert moved[m].all() or kept[m].all(), (a, b)
    # two trades put every cell back
    twice = run(ctx, "blocks", pic, amount=2.0, cell=8.0, drift=0.0, angle=angle, spread=0.0,
                action=swap, rule=choice("blocks", "rule", rule))
    assert np.array_equal(twice[whole], pic[whole])


def test_spread_zero_puts_every_block_in_step_random_included(ctx):
    for rule in ("rows", "diagonal", "random"):
        px = run(ctx, "blocks", white_line(), amount=0.5, cell=8.0, drift=0.0, spread=0.0,
                 rule=choice("blocks", "rule", rule))
        assert set(column(px)) == {W // 2 - 4}, rule         # one slide, the whole frame
    apart = run(ctx, "blocks", white_line(), amount=0.5, cell=8.0, drift=0.0, spread=0.5,
                rule=choice("blocks", "rule", "random"))
    assert len(set(column(apart))) > 2


@pytest.mark.parametrize("aspect", [1.0, 2.0, 0.5])
def test_a_bulge_is_a_circle_and_leaves_the_rest_of_the_cell_alone(ctx, aspect):
    """The lens lives inside the cell's inscribed circle, measured in px, so
    it is a circle in a cell of any Aspect: outside it the picture is
    untouched, which is what keeps cells joined."""
    pic = speckle()
    cw, ch = 16.0 * aspect, 16.0
    px = run(ctx, "blocks", pic, amount=2.0, cell=ch, aspect=aspect, drift=0.0,
             action=choice("blocks", "action", "bulge"), rule=choice("blocks", "rule", "rows"))
    yy, xx = np.mgrid[0:H, 0:W]
    # a cell sits on the frame's centre: its own centre is (W/2, H/2)
    lx = (xx + 0.5 - W / 2 + cw / 2) % cw - cw / 2
    ly = (yy + 0.5 - H / 2 + ch / 2) % ch - ch / 2
    r = min(cw, ch) / 2
    outside = np.hypot(lx, ly) > r + 0.5
    assert np.array_equal(px[outside], pic[outside])
    inside = np.hypot(lx, ly) < r - 1.5
    assert (px[inside] != pic[inside]).any(axis=-1).mean() > 0.5


def test_the_grid_moves_with_drift_and_holds_without(ctx):
    line = white_line()
    still = frames(ctx, "blocks", line, [0.0, 0.4], amount=0.5, cell=8.0, drift=0.0)
    assert np.array_equal(*still)
    moving = frames(ctx, "blocks", line, [0.0, 0.2], amount=0.5, cell=8.0, drift=1.0)
    assert not np.array_equal(*moving)
