"""Wave Table (shaders/fx/wavetable.glsl): a disc of the picture at each root,
pasted along a path up to Position × Length.

What holds it here, through the pass the app runs (`FxChain.run_one`):
Position 0 and every pixel no paste covers are the input byte for byte, and
a relief profile shades the tube's cross-section. What it looks like is
judged by eye. A test that needs a known geometry (or the slow, sure way of
solving what the shader solves exactly) patches a copy of the file, and
`patched` fails if the text it means to patch has gone.
"""

import shutil

import numpy as np
import pytest

from hyperspace.fx import FX_DIR, FxChain, FxState

NAME = "wavetable"
SOURCE = (FX_DIR / f"{NAME}.glsl").read_text()
PROFILES = ("rim", "round", "bevel", "ridge", "groove", "fluted", "flat")


def patched(*swaps: tuple[str, str]) -> str:
    text = SOURCE
    for old, new in swaps:
        assert old in text, f"wavetable.glsl no longer has: {old}"
        text = text.replace(old, new)
    return text


@pytest.fixture
def fxdir(tmp_path):
    d = tmp_path / "fx"
    d.mkdir()
    shutil.copy(FX_DIR / "_lib.glsl", d / "_lib.glsl")
    return d


def run(ctx, picture: np.ndarray, directory=FX_DIR, **values) -> np.ndarray:
    """`picture` (h, w, RGBA floats) through the effect on half floats, the
    pool's format, as the graph runs it."""
    st = FxState(directory)
    st.values[NAME].update(values)
    chain = FxChain(ctx, st)
    h, w = picture.shape[:2]
    (src, _), _ = chain.pool((w, h))
    src.write(picture.astype(np.float16).tobytes())
    out = ctx.texture((w, h), 4, dtype="f2")
    fbo = ctx.framebuffer(color_attachments=[out])
    chain.run_one(NAME, src, fbo, 0.0, opaque=0)
    assert chain.errors == {}
    got = np.frombuffer(out.read(), dtype=np.float16).reshape(h, w, 4).copy()
    fbo.release()
    out.release()
    return got


def noise(w=192, h=120) -> np.ndarray:
    """Premultiplied half floats no two of which agree: a linear read that
    lands a step off shows (the alpha covers the colour, as a pass makes it)."""
    rgb = np.random.default_rng(3).random((h, w, 3), dtype=np.float32)
    return np.concatenate([rgb, rgb.max(axis=2, keepdims=True)], axis=2).astype(np.float16)


# ---------------------------------------------------------------- the input, exactly


@pytest.mark.parametrize("settings", [
    {},
    {"mode": 1, "blades": 5, "stagger": 1.0, "profile": 3, "depth": 1.0},
    {"mode": 2, "brush": 0.5, "length": 1.5, "jitter": 1.0, "profile": 1},
    {"scale": 24.0, "density": 0.4, "offset_x": 0.3, "offset_y": -0.7, "trail": 0.0},
], ids=["defaults", "noodles", "curls", "fine"])
def test_position_0_is_the_input_byte_for_byte(ctx, settings):
    want = noise()
    assert np.array_equal(run(ctx, want, pos=0.0, **settings), want)


def test_a_pixel_no_paste_covers_is_the_input_byte_for_byte(ctx):
    """Density 0 grows no path, wherever Position is: the whole frame is
    uncovered (a feedback loop through the effect would add up a step a pass)."""
    want = noise()
    assert np.array_equal(run(ctx, want, pos=1.0, density=0.0), want)


# ---------------------------------------------------------------- the profiles

SIZE, SCALE, BRUSH, DEPTH = 256, 2.0, 0.3, 0.8
# straight paths heading +x from the cell's middle: at this scale the root of
# cell (0, 0) is at p = (0.5, 0.5), and its tube reaches past p.x = 0.85
# with no neighbour's on top of it there
STRAIGHT_EAST = (
    ("float fi = float(i);", "return 0.0; float fi = float(i);"),
    ("float delay =", "th = 0.0; float delay ="),
)


def straight_tube_light(ctx, fxdir, profile: str):
    """The light down a column of the tube well behind its head, and how far
    each pixel of it lies from the path, in brushes."""
    (fxdir / f"{NAME}.glsl").write_text(patched(*STRAIGHT_EAST))
    grey = np.ones((SIZE, SIZE, 4), np.float32) * [0.5, 0.5, 0.5, 1.0]
    got = run(ctx, grey, fxdir, pos=1.0, scale=SCALE, jitter=0.0, brush=BRUSH, length=0.9,
              depth=DEPTH, profile=float(PROFILES.index(profile)))
    column = int((0.85 / SCALE + 0.5) * SIZE)
    py = ((np.arange(SIZE) + 0.5) / SIZE - 0.5) * SCALE
    inside = np.abs(py - 0.5) < 0.93 * BRUSH
    return np.asarray(got[inside, column, 0], np.float64) / 0.5, (py[inside] - 0.5) / BRUSH


def relief(profile: str, y: np.ndarray) -> np.ndarray:
    """profile() in the shader, in numpy, at x = (0, y): across the tube."""
    d = np.abs(y)
    slope = {
        "round": -d / np.sqrt(np.maximum(1.0 - d * d, 0.04)),
        "bevel": np.where(d < 0.6, 0.0, -2.5),
        "ridge": np.full_like(d, -1.5),
        "groove": 2.0 * d,
        "fluted": -2.5 * np.sin(d * 3.0 * np.pi),
    }[profile]
    gy = slope * np.sign(y)
    n = np.stack([np.zeros_like(y), -gy, np.ones_like(y)], axis=1)
    n /= np.linalg.norm(n, axis=1, keepdims=True)
    l = np.array([-0.5, 0.6, 0.6]) / np.linalg.norm([-0.5, 0.6, 0.6])
    return 1.0 + (np.clip(n @ l / l[2], 0.0, 1.6) - 1.0) * DEPTH


@pytest.mark.parametrize("profile", ["round", "bevel", "ridge", "groove", "fluted"])
def test_a_relief_profile_is_the_tubes_cross_section(ctx, fxdir, profile):
    """Behind the head a pixel's furthest paste has it at the stamp's edge
    whatever its distance from the path, so the relief is read from the
    nearest point of the path instead: the light is a function of how far
    across the tube a pixel lies."""
    light, y = straight_tube_light(ctx, fxdir, profile)
    assert np.allclose(light, relief(profile, y), atol=0.02)


def test_rim_darkens_the_tube_evenly(ctx, fxdir):
    """Rim is each paste's own edge, and behind the head a pixel is at the edge
    of its last paste: one even shade, the head's disc lit. The look the
    owner approved as the default."""
    light, _ = straight_tube_light(ctx, fxdir, "rim")
    assert np.allclose(light, 1.0 - DEPTH, atol=0.01)


def test_flat_leaves_the_copies_as_they_are(ctx, fxdir):
    light, _ = straight_tube_light(ctx, fxdir, "flat")
    assert np.allclose(light, 1.0, atol=0.002)
