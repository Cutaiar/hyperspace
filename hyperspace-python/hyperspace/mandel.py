"""The Mandelbrot effect's Python half (plan 63): `shaders/fx/mandel.glsl`
says `// @hook mandel`, so `fx.FxChain.run_one` hands its pass here and
`fx.FxState.advance` its drives.

The iteration is z → z^p + c with every term a param: the start z₀, the
constant c and the whole-number exponent p (2–8). A pixel's point q in the
plane is laid into the two terms by **Slice** s: c = mix(q, c, s) and
z₀ = mix(z₀, q, s), so s = 0 is the Mandelbrot set (z₀ fixed, 0 by default)
and s = 1 a Julia set (c fixed), with a tilt through both between
(2swap's "Mandelbrot's Evil Twin").

Three things live here and not in the shader:

- **The drives** (`advance`). Pan x/y, Dive and the c and z₀ drives are rates,
  integrated in float64 into the terms every frame they run, in *view
  heights* a second (`VIEW` / zoom): a knob, a hand or an LFO on one moves
  the picture by the same amount on screen at any depth (owner decision 4).
  The terms stay absolute, saved values. The rule of `@clock` (no shader
  multiplies time by a param) holds: the shader only ever reads where the
  view is.
- **The tier** (`perturbs`). Float32 direct iteration to `PERTURB_AT` (10⁴×),
  then perturbation: a reference orbit Z₀ … Z_N in float64 here
  (`reference_orbit`), uploaded as an RG32F texture `REF_W` wide, and each
  pixel iterates δₙ₊₁ = (Zₙ + δₙ)^p − Zₙ^p + δc in float32, the difference
  expanded by the binomial theorem (`binomial_delta`), with δ₀ = δz₀. When the
  full z = Zₙ + δₙ is nearer the orbit's start than δ is to the reference, or
  the reference runs out, δ becomes z − Z₀ and the index restarts (`rebase`,
  Zhuoran's rule; with Z₀ = 0 it is |Z + δ| < |δ|). The reference is kept
  while its terms hold and it is still in view (`Reference.stale`).
- **The size and the skip** (`run`). The pass renders at 540, 810 or 1080
  lines and is upscaled to its output. With the inside black, on a slice
  whose set has no holes (p whole and z₀ = 0, or a pure Julia slice:
  `skip_valid`), two pre-passes first flag every 16×16 tile whose whole
  border is inside (Mariani–Silver, `tile_flags`), and the picture pass fills
  those black without iterating.

The numpy functions here are the float64 oracles the tests hold the shader
to: `escape_counts` (the direct iteration, with the shader's periodicity
check optional), `perturbed_counts` (the perturbation recurrence and the
rebase, in float32 or float64), `tile_flags` / `fill_tiles` (the border rule).

Hot reload: the GL objects live on the chain (`FxChain.mandel`), never at
module level, so a reload of this module keeps them; a reload of the shader
file is fx.py's as for any effect.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, cast

import moderngl
import numpy as np

from .glsl import QUAD_VS

VIEW = 3.0              # plane units top to bottom at zoom 1
SIZES = (540, 810, 1080)     # the Size choice's lines (owner decision 2)
PERTURB_AT = 1.0e4      # auto: float32 direct up to here, perturbation past it (decision 3)
REF_W = 1024            # the reference texture's width (mandel.glsl's REF_W)
BAIL = 1.0e4            # |z|² past this has escaped (mandel.glsl's BAIL)
TILE = 16               # the skip's tile, px (mandel.glsl's TILE)
DIVE_DOUBLINGS = 4.0    # Dive at ±1: zoom doublings a second
PERIOD_EPS = 0.05       # periodicity: z within this many pixels of a saved z is a cycle
TIERS = ("auto", "direct", "perturb")
DRIVES = (("centre_x", "pan_x"), ("centre_y", "pan_y"),
          ("c_x", "c_drive_x"), ("c_y", "c_drive_y"),
          ("z0_x", "z0_drive_x"), ("z0_y", "z0_drive_y"))


# ---- the maths, float64 oracles and the shader's twins ----

def view_height(zoom: float) -> float:
    """The plane units from the bottom of the view to its top."""
    return VIEW / max(float(zoom), 1e-300)


def offsets(w: int, h: int, zoom: float) -> np.ndarray:
    """Each pixel's offset from the view's centre in the plane, complex128,
    (h, w), row 0 at the bottom — the shader's `off` at the pixel's centre."""
    x = (np.arange(w) + 0.5) / w - 0.5
    y = (np.arange(h) + 0.5) / h - 0.5
    k = view_height(zoom)
    return (x[None, :] * (w / h) * k) + 1j * (y[:, None] * k)


def terms(q, v: dict) -> tuple[Any, Any]:
    """(c, z₀) for plane point(s) `q` under the values `v`: Slice s lays q into
    c at 0 and into z₀ at 1."""
    s = float(v["slice"])
    c = complex(v["c_x"], v["c_y"])
    z0 = complex(v["z0_x"], v["z0_y"])
    return q + s * (c - q), z0 + s * (q - z0)


def smooth(n, r2, p: int):
    """The smooth escape count n + 1 − log_p log|z| (owner decision 5), at
    least 0, from the step n and |z|² just past the bail-out."""
    return np.maximum(n + 1.0 - np.log(0.5 * np.log(r2)) / math.log(p), 0.0)


def in_cardioid(c) -> np.ndarray:
    """The closed-form inside test for p = 2, z₀ = 0: the main cardioid and the
    period-2 bulb."""
    c = np.asarray(c, dtype=np.complex128)
    x, y = c.real - 0.25, c.imag
    q = x * x + y * y
    return (q * (q + x) <= 0.25 * y * y) | ((c.real + 1.0) ** 2 + y * y <= 0.0625)


def escape_counts(c, z0, p: int, iters: int, *, periodic_eps: float | None = None,
                  dtype=np.complex128) -> tuple[np.ndarray, np.ndarray]:
    """The direct iteration over arrays of c and z₀: (count, inside). count is
    the smooth count where a point escaped, else the step a cycle was caught
    at (`periodic_eps`: the shader's check, Brent's doubling window, |z −
    saved| < eps) or `iters`. With no `periodic_eps` it is the plain oracle."""
    c = np.asarray(c, dtype=dtype)
    z = np.broadcast_to(np.asarray(z0, dtype=dtype), c.shape).copy()
    count = np.full(c.shape, float(iters))
    inside = np.ones(c.shape, bool)
    live = np.ones(c.shape, bool)
    saved = z.copy()
    lim, since = 8, 0
    eps2 = None if periodic_eps is None else periodic_eps * periodic_eps
    for n in range(iters):
        zl = z[live]
        zl = zl ** p + c[live]
        z[live] = zl
        r2 = (z.real.astype(np.float64) ** 2 + z.imag.astype(np.float64) ** 2)
        out = live & (r2 > BAIL)
        if out.any():
            count[out] = smooth(n, r2[out], p)
            inside[out] = False
            live &= ~out
        if eps2 is not None:
            d = z - saved
            caught = live & ((d.real.astype(np.float64) ** 2 + d.imag.astype(np.float64) ** 2)
                             < eps2)
            if caught.any():
                count[caught] = n
                live &= ~caught
            since += 1
            if since == lim:
                saved = z.copy()
                since, lim = 0, lim * 2
        if not live.any():
            break
    return count, inside


def reference_orbit(c: complex, z0: complex, p: int, iters: int) -> np.ndarray:
    """Z₀ = z₀ … Z_N in float64 at one point: N = `iters`, or the first step
    past the bail-out (that escaped value is the orbit's last entry, so a
    pixel reading it rebases)."""
    out = np.empty(iters + 1, np.complex128)
    z = complex(z0)
    out[0] = z
    for n in range(iters):
        z = z ** p + c
        out[n + 1] = z
        if z.real * z.real + z.imag * z.imag > BAIL:
            return out[:n + 2]
    return out


def binomial_delta(Z, d, p: int):
    """(Z + d)^p − Z^p by the binomial theorem, Horner in d — the shader's
    `binomial_delta`: no two large terms cancel, so it holds while d is many
    orders under Z."""
    zp = [np.ones_like(Z)]
    for _ in range(1, p):
        zp.append(zp[-1] * Z)
    s = np.ones_like(d)
    coef = 1.0
    for k in range(p - 1, 0, -1):
        coef = coef * (k + 1) / (p - k)          # C(p, k), walked down from k = p
        s = s * d + coef * zp[p - k]
    return s * d


def rebase(z, d, Z0) -> np.ndarray:
    """Where the rebase fires: the full z nearer the orbit's start Z₀ than δ
    is to the reference (with Z₀ = 0, |Z + δ| < |δ|). The rule; the iteration
    takes z − Z₀ part by part, (Zₘ − Z₀) + δ (`perturbed_counts`)."""
    return np.abs(z - Z0) < np.abs(d)


def perturbed_counts(ref: np.ndarray, dc, dz0, p: int, iters: int, *,
                     periodic_eps: float | None = None, dtype=np.complex64,
                     rebasing: bool = True) -> tuple[np.ndarray, np.ndarray, int]:
    """The perturbation tier over arrays of δc and δz₀ against the reference
    `ref` (`reference_orbit`), δ in `dtype` (float32 as the shader, or float64)
    and the reference read in it too: (count, inside, rebases) — the same
    counts as `escape_counts` at c_ref + δc, z₀_ref + δz₀. `rebasing` False
    (tests only) keeps the rule out but for the reference running out, to show
    what it is for."""
    R = ref.astype(dtype)
    last = len(ref) - 1
    dc = np.asarray(dc, dtype=dtype)
    d = np.broadcast_to(np.asarray(dz0, dtype=dtype), dc.shape).copy()
    m = np.zeros(dc.shape, np.int64)
    Z0 = R[0]
    # a z is its reference value and its δ, never their float32 sum subtracted
    # from another: deep in, that sum has lost δ's digits (the shader's rule)
    savedZ = np.full(dc.shape, Z0, dtype=dtype)
    savedD = d.copy()
    count = np.full(dc.shape, float(iters))
    inside = np.ones(dc.shape, bool)
    live = np.ones(dc.shape, bool)
    lim, since, rebases = 8, 0, 0
    eps2 = None if periodic_eps is None else periodic_eps * periodic_eps
    for n in range(iters):
        idx = np.flatnonzero(live)
        if idx.size == 0:
            break
        dl, ml = d.flat[idx], m.flat[idx]
        dl = binomial_delta(R[ml], dl, p) + dc.flat[idx]
        ml = ml + 1
        zl = R[ml] + dl
        r2 = zl.real.astype(np.float64) ** 2 + zl.imag.astype(np.float64) ** 2
        out = r2 > BAIL
        back = (R[ml] - Z0) + dl                 # z − Z₀, part by part
        near = np.abs(back) < np.abs(dl)         # `rebase`'s rule
        reb = ~out & ((ml >= last) | (near if rebasing else False))
        rebases += int(reb.sum())
        dl = np.where(reb, back, dl)
        ml = np.where(reb, 0, ml)
        d.flat[idx], m.flat[idx] = dl, ml
        gone = idx[out]
        count.flat[gone] = smooth(n, r2[out], p)
        inside.flat[gone] = False
        live.flat[gone] = False
        if eps2 is not None:
            Zm = R[m]
            e = (Zm - savedZ) + (d - savedD)
            caught = live & ((e.real.astype(np.float64) ** 2 + e.imag.astype(np.float64) ** 2)
                             < eps2)
            count[caught] = n
            live &= ~caught
            since += 1
            if since == lim:
                savedZ, savedD = Zm.copy(), d.copy()
                since, lim = 0, lim * 2
    return count, inside, rebases


def is_edge(w: int, h: int) -> np.ndarray:
    """(h, w): True on a tile's border — its first or last row or column, or
    the picture's last when the tile is cut short there."""
    x, y = np.arange(w), np.arange(h)
    ex = (x % TILE == 0) | (x % TILE == TILE - 1) | (x == w - 1)
    ey = (y % TILE == 0) | (y % TILE == TILE - 1) | (y == h - 1)
    return ex[None, :] | ey[:, None]


def tile_flags(inside: np.ndarray) -> np.ndarray:
    """Mariani–Silver's rule over an (h, w) inside mask: (⌈h/16⌉, ⌈w/16⌉), True
    where the tile's whole border is inside. Only the border is read — what
    the shader's first pass computes."""
    h, w = inside.shape
    th, tw = -(-h // TILE), -(-w // TILE)
    out = np.zeros((th, tw), bool)
    for ty in range(th):
        for tx in range(tw):
            t = inside[ty * TILE:min((ty + 1) * TILE, h), tx * TILE:min((tx + 1) * TILE, w)]
            out[ty, tx] = bool(t[0].all() and t[-1].all() and t[:, 0].all() and t[:, -1].all())
    return out


def fill_tiles(inside: np.ndarray) -> np.ndarray:
    """The inside mask the skip draws: a flagged tile filled whole, every other
    pixel as iterated."""
    flags = tile_flags(inside)
    h, w = inside.shape
    filled = np.repeat(np.repeat(flags, TILE, 0), TILE, 1)[:h, :w]
    return inside | filled


def skip_valid(v: dict) -> bool:
    """Whether the skip may run: on, the inside black (a coloured inside needs
    every pixel's settling time), and a slice whose set has no holes — the
    Mandelbrot slice with z₀ = 0, or a pure Julia slice (owner's rule)."""
    if int(v["skip"]) != 0 or int(v["interior"]) != 0:
        return False
    s = float(v["slice"])
    return (s == 0.0 and float(v["z0_x"]) == 0.0 and float(v["z0_y"]) == 0.0) or s == 1.0


def steps(v: dict) -> int:
    """The iteration cap: Steps is a float knob on a log taper, rounded as the
    shader rounds it."""
    return int(float(v["iters"]) + 0.5)


def perturbs(v: dict) -> bool:
    """Whether the pass runs the perturbation tier: Tier's choice, auto past
    `PERTURB_AT`."""
    t = TIERS[int(v["tier"])] if 0 <= int(v["tier"]) < len(TIERS) else "auto"
    return t == "perturb" or (t == "auto" and float(v["zoom"]) > PERTURB_AT)


def render_size(size: int, w: int, h: int) -> tuple[int, int]:
    """The render target for the Size choice `size` over an output rect w × h:
    that many lines at the output's aspect, or the output itself when it has
    no more lines than that."""
    lines = SIZES[max(0, min(int(size), len(SIZES) - 1))]
    if h <= lines or w <= 0 or h <= 0:
        return w, h
    return max(1, round(lines * w / h)), lines


# ---- the drives (FxState.advance) ----

def advance(spec, v: dict, dt: float) -> None:
    """Each drive's rate into its term, in view heights a second, and Dive into
    the zoom in doublings a second; clamped to each param's range. A rate at
    0 writes nothing."""
    if dt <= 0.0:
        return
    rng = {p.key: (p.lo, p.hi) for p in spec.params}
    dive = float(v.get("dive", 0.0))
    if dive:
        lo, hi = rng["zoom"]
        v["zoom"] = min(max(float(v["zoom"]) * 2.0 ** (DIVE_DOUBLINGS * dive * dt), lo), hi)
    h = view_height(v["zoom"])
    for term, rate in DRIVES:
        r = float(v.get(rate, 0.0))
        if r:
            lo, hi = rng[term]
            v[term] = min(max(float(v[term]) + r * h * dt, lo), hi)


# ---- the reference orbit ----

@dataclass
class Reference:
    """The reference orbit uploaded for one effect instance: the point Q it is
    at, the terms it was made under, its length, its texture."""

    q: complex = 0j
    key: tuple = ()
    n: int = 0
    tex: moderngl.Texture | None = None

    def stale(self, v: dict, aspect: float) -> bool:
        """New terms, a longer cap than an orbit that ran it out, or the point
        out of the view."""
        if self.tex is None or self.key != terms_key(v):
            return True
        half = 0.5 * view_height(v["zoom"])
        d = complex(v["centre_x"], v["centre_y"]) - self.q
        return abs(d.real) > half * aspect or abs(d.imag) > half

    def make(self, ctx: moderngl.Context, v: dict) -> None:
        """Compute the orbit at the view's centre and upload it."""
        self.q = complex(v["centre_x"], v["centre_y"])
        self.key = terms_key(v)
        c, z0 = terms(self.q, v)
        orbit = reference_orbit(c, z0, int(v["power"]), steps(v))
        self.n = len(orbit) - 1
        rows = -(-len(orbit) // REF_W)
        data = np.zeros((rows * REF_W, 2), np.float32)
        data[:len(orbit)] = orbit.view(np.float64).reshape(-1, 2)    # (re, im) pairs
        if self.tex is not None and self.tex.size != (REF_W, rows):
            self.tex.release()
            self.tex = None
        if self.tex is None:
            self.tex = ctx.texture((REF_W, rows), 2, dtype="f4")
            self.tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
        self.tex.write(data.tobytes())

    def release(self) -> None:
        if self.tex is not None:
            self.tex.release()
            self.tex = None


def terms_key(v: dict) -> tuple:
    """What a reference orbit depends on besides where it is."""
    return (int(v["power"]), steps(v), float(v["slice"]),
            float(v["c_x"]), float(v["c_y"]), float(v["z0_x"]), float(v["z0_y"]))


# ---- the pass ----

TILES_FS = """
#version 330
uniform sampler2D u_border;   // the border pass: r 1 where a border pixel is inside
uniform ivec2 u_size;         // the render target, px
out vec4 f_color;
void main() {
    ivec2 o = ivec2(gl_FragCoord.xy) * 16;
    ivec2 e = min(o + 15, u_size - 1);
    float every = 1.0;
    for (int x = o.x; x <= e.x; x++)
        every = min(every, min(texelFetch(u_border, ivec2(x, o.y), 0).r,
                           texelFetch(u_border, ivec2(x, e.y), 0).r));
    for (int y = o.y; y <= e.y; y++)
        every = min(every, min(texelFetch(u_border, ivec2(o.x, y), 0).r,
                           texelFetch(u_border, ivec2(e.x, y), 0).r));
    f_color = vec4(every, 0.0, 0.0, 1.0);
}
"""


@dataclass
class Target:
    """A texture and its framebuffer at one size, remade when it changes."""

    size: tuple[int, int] = (0, 0)
    tex: moderngl.Texture | None = None
    fbo: moderngl.Framebuffer | None = None

    def at(self, ctx: moderngl.Context, size: tuple[int, int], dtype: str = "f2"
           ) -> moderngl.Framebuffer:
        if self.fbo is None or self.size != tuple(size):
            self.release()
            self.tex = ctx.texture(size, 4, dtype=dtype)
            self.tex.repeat_x = self.tex.repeat_y = False
            self.fbo = ctx.framebuffer(color_attachments=[self.tex])
            self.size = (int(size[0]), int(size[1]))
        return self.fbo

    def release(self) -> None:
        for res in (self.fbo, self.tex):
            if res is not None:
                res.release()
        self.fbo = self.tex = None
        self.size = (0, 0)


@dataclass
class State:
    """One effect instance's GL objects on one chain."""

    ref: Reference = field(default_factory=Reference)
    low: Target = field(default_factory=Target)       # the Size's render target
    border: Target = field(default_factory=Target)    # the skip's first pass
    tiles: Target = field(default_factory=Target)     # one texel a tile
    stats: dict = field(default_factory=dict)         # the last pass's choices (tools, tests)

    def release(self) -> None:
        for t in (self.ref, self.low, self.border, self.tiles):
            t.release()


@dataclass
class Gl:
    """Everything this module made on one chain's context: the tiles program
    and each instance's `State`. Lives on the chain (`FxChain.mandel`)."""

    states: dict[str, State] = field(default_factory=dict)
    tiles_prog: moderngl.Program | None = None
    tiles_vao: moderngl.VertexArray | None = None

    def state(self, name: str) -> State:
        return self.states.setdefault(name, State())

    def prune(self, names) -> None:
        """Release every instance's objects that is not among `names` (a
        node deleted, a patch loaded without it)."""
        for name in [n for n in self.states if n not in names]:
            self.states.pop(name).release()

    def tiles(self, ctx: moderngl.Context):
        if self.tiles_prog is None:
            self.tiles_prog = ctx.program(vertex_shader=QUAD_VS, fragment_shader=TILES_FS)
            self.tiles_vao = ctx.vertex_array(self.tiles_prog, [])
            _set(self.tiles_prog, "u_border", 0)
        assert self.tiles_vao is not None
        return self.tiles_prog, self.tiles_vao

    def release(self) -> None:
        for s in self.states.values():
            s.release()
        self.states.clear()
        for res in (self.tiles_vao, self.tiles_prog):
            if res is not None:
                res.release()
        self.tiles_prog = self.tiles_vao = None


def tick(chain) -> None:
    """Once a frame (`FxChain.tick`): free the objects of instances that no
    longer exist, and drop them all after a hot reload of this module (a live
    `Gl` of the old class, its helpers and its tile program built from the
    old source) — rebuilt on next use."""
    gl = getattr(chain, "mandel", None)
    if gl is None:
        return
    if type(gl) is not Gl:
        gl.release()
        chain.mandel = None
        return
    if gl.states:
        gl.prune(chain.state.specs)


def gl_of(chain) -> Gl:
    """The chain's `Gl`, made on first use (a chain from before a hot reload of
    fx.py has none yet)."""
    got = getattr(chain, "mandel", None)
    if got is None:
        got = chain.mandel = Gl()
    return got


def _set(prog: moderngl.Program, name: str, value) -> None:
    if name in prog:
        cast(moderngl.Uniform, prog[name]).value = value


def _get(prog: moderngl.Program, name: str) -> Any:
    return cast(moderngl.Uniform, prog[name]).value if name in prog else None


def _tex(t: Target | Reference) -> moderngl.Texture:
    assert t.tex is not None
    return t.tex


def run(chain, name: str, prog: moderngl.Program, vao: moderngl.VertexArray,
        src: moderngl.Texture, dst: moderngl.Framebuffer) -> None:
    """The effect's pass (from `FxChain.run_one`, every uniform of the file
    already set): the tier's uniforms, the skip's two pre-passes when valid,
    the picture at the Size's lines, and the upscale into `dst`."""
    ctx = chain.ctx
    gl = gl_of(chain)
    st = gl.state(name)
    v = chain.state.values[name]
    vx, vy, vw, vh = (int(x) for x in dst.viewport)
    w, h = render_size(int(v["size"]), vw, vh)
    direct = (w, h) == (vw, vh)
    pert = perturbs(v)
    if pert:
        if st.ref.stale(v, w / h):
            st.ref.make(ctx, v)
            st.stats["references"] = st.stats.get("references", 0) + 1
        shift = complex(v["centre_x"], v["centre_y"]) - st.ref.q
        c, z0 = terms(st.ref.q, v)
        _tex(st.ref).use(location=2)
        _set(prog, "u_ref", 2)
        _set(prog, "u_ref_n", int(st.ref.n))
        _set(prog, "u_shift_x", float(shift.real))
        _set(prog, "u_shift_y", float(shift.imag))
    else:
        c, z0 = complex(v["c_x"], v["c_y"]), complex(v["z0_x"], v["z0_y"])
        _set(prog, "u_view_x", float(v["centre_x"]))
        _set(prog, "u_view_y", float(v["centre_y"]))
    _set(prog, "u_perturb", int(pert))
    _set(prog, "u_ref_cx", float(c.real))
    _set(prog, "u_ref_cy", float(c.imag))
    _set(prog, "u_ref_zx", float(z0.real))
    _set(prog, "u_ref_zy", float(z0.imag))
    _set(prog, "u_lines", int(h))
    _set(prog, "u_width", int(w))
    scaled = int((w, h) != tuple(src.size))
    skip = skip_valid(v)
    st.stats.update(size=(w, h), perturb=pert, skip=skip)
    _set(prog, "u_tiles_on", 0)
    if skip:
        # the borders, flags only: the effect's own output, unblended
        mix, blend, opaque = (_get(prog, k) for k in ("u_mix", "u_blend", "u_opaque"))
        fbo = st.border.at(ctx, (w, h), dtype="f1")
        fbo.use()
        _set(prog, "u_pass", 1)
        _set(prog, "u_mix", 1.0)
        _set(prog, "u_blend", 0)
        _set(prog, "u_opaque", 1)
        _set(prog, "u_scaled", scaled)
        _set(prog, "u_origin", (0, 0))
        vao.render(moderngl.TRIANGLES, vertices=3)
        for k, x in (("u_mix", mix), ("u_blend", blend), ("u_opaque", opaque)):
            if x is not None:
                _set(prog, k, x)
        tprog, tvao = gl.tiles(ctx)
        tfbo = st.tiles.at(ctx, (-(-w // TILE), -(-h // TILE)), dtype="f1")
        tfbo.use()
        _tex(st.border).use(location=0)
        _set(tprog, "u_size", (w, h))
        tvao.render(moderngl.TRIANGLES, vertices=3)
        _tex(st.tiles).use(location=3)
        _set(prog, "u_tiles", 3)
        _set(prog, "u_tiles_on", 1)
        src.use(location=0)
    _set(prog, "u_pass", 0)
    if direct:
        dst.use()
        _set(prog, "u_scaled", scaled)
        _set(prog, "u_origin", (vx, vy))
        vao.render(moderngl.TRIANGLES, vertices=3)
        return
    low = st.low.at(ctx, (w, h))
    low.use()
    _set(prog, "u_scaled", scaled)
    _set(prog, "u_origin", (0, 0))
    vao.render(moderngl.TRIANGLES, vertices=3)
    # the upscale: the chain's copy, read through its LINEAR sampler
    chain.upscale(_tex(st.low), dst)
