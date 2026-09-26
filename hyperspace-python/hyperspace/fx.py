"""Effects — a stack of fullscreen shader passes over the finished frame.

An effect is one GLSL file in ``hyperspace/shaders/fx/``: a function
``vec4 effect(vec2 uv)`` plus the uniforms it reads, each annotated so the
registry can declare it. Nothing about an effect lives in Python — drop a
file in the folder and it appears on the FX page with its faders, as
ordinary registry params (``fx.<file>.<uniform>``): MIDI-learnable,
routable from an audio lane, saved by presets and projects. Edit a file
while the app runs and it recompiles on save; a compile error keeps the
last good program and shows the message on the page.

The file format (see any file in the folder; ``_lib.glsl`` holds the
helpers every effect can call)::

    // @label  Trip warp            the name on the page
    // @order  20                   where it sits in the stack (low runs first)
    // @blend  mix                  mix | add | screen | multiply — how its
                                    output lands on its input
    // @speed  1                    the default time rate
    // @tip    …                    one line for the tooltip
    uniform float u_amount;  // @param 0 2 0.5 "Amount" tooltip text…
    uniform float u_scale;   // @param 0.5 12 3 log "Scale" …
    uniform int   u_count;   // @param 2 16 6 "Count" …    (int uniform → integer param)
    vec4 effect(vec2 uv) { return src(uv + …); }

``@param lo hi default [log] [wrap] "Label" tip`` — the uniform name
without its ``u_`` is the id suffix. Every effect also gets five params
of its own: ``on``, ``mix`` (wet/dry against its input), ``speed`` (the
rate its clock ``u_phase`` runs at — integrated here, so a lane riding
the speed never jumps the phase), ``blend`` and ``order``. Two more are
the chain's: ``fx.on`` (bypass everything) and ``fx.mix`` (scales every
effect's mix — one fader that fades the whole trip in).

The frame (render.py): the scene is drawn, the look-back composites it
into the first of two ping-pong textures instead of the window, each
active effect reads one and writes the other, and the last writes the
window. With no effect on the chain is not in the path at all and the
output is bit-identical to before. The look-back captures the scene, not
the effected frame, so echoes are never warped twice.

Colour stays premultiplied (overlay.py clears to see-through): after its
blend a pass lifts alpha to cover its own colour, so a generator painting
over a transparent ground shows on the desktop.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import moderngl

FX_DIR = Path(__file__).parent / "shaders" / "fx"
LIB_FILE = "_lib.glsl"          # helpers prepended to every effect; not an effect
BLENDS = ["mix", "add", "screen", "multiply"]
RESERVED = {"on", "mix", "speed", "blend", "order"}   # the per-effect params' names
MAX_ORDER = 99
SPEED_MAX = 8.0
RELOAD_EVERY = 30               # frames between mtime checks of the folder

_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
_DIRECTIVE = re.compile(r"^\s*//\s*@(label|order|blend|speed|tip)\s+(.*?)\s*$")
_UNIFORM = re.compile(r"^\s*uniform\s+(float|int)\s+(u_\w+)\s*;\s*//\s*@param\s+(.*?)\s*$")
_PARAM = re.compile(
    r"^(?P<nums>(?:[-+]?[\d.]+(?:[eE][-+]?\d+)?\s+){3})"
    r"(?P<flags>(?:(?:log|wrap)\s+)*)\"(?P<label>[^\"]+)\"\s*(?P<tip>.*)$"
)


class SpecError(ValueError):
    pass


@dataclass
class ParamSpec:
    """One annotated uniform."""

    key: str            # the id suffix: the uniform name without u_
    uniform: str
    label: str
    lo: float
    hi: float
    default: float
    integer: bool = False
    log: bool = False
    wrap: bool = False
    tip: str = ""


@dataclass
class EffectSpec:
    """One effect file, parsed."""

    name: str
    label: str
    source: str
    params: list[ParamSpec] = field(default_factory=list)
    order: int = 50
    blend: int = 0
    speed: float = 1.0
    tip: str = ""

    def signature(self) -> tuple:
        """What the registry declares from this spec — a change means re-declare."""
        return (self.label, self.tip, self.order, self.blend, self.speed,
                tuple((p.key, p.label, p.lo, p.hi, p.default, p.integer, p.log, p.wrap, p.tip)
                      for p in self.params))


def parse(name: str, source: str) -> EffectSpec:
    """An effect file's text → its spec. Raises SpecError on a bad header."""
    if not _NAME.match(name):
        raise SpecError(f"{name}: file names are lower_snake_case")
    spec = EffectSpec(name=name, label=name.replace("_", " "), source=source)
    seen: set[str] = set()
    for n, line in enumerate(source.splitlines(), 1):
        m = _DIRECTIVE.match(line)
        if m:
            key, val = m.groups()
            try:
                if key == "label":
                    spec.label = val
                elif key == "tip":
                    spec.tip = f"{spec.tip} {val}".strip()
                elif key == "order":
                    spec.order = max(0, min(int(val), MAX_ORDER))
                elif key == "speed":
                    spec.speed = float(val)
                elif key == "blend":
                    spec.blend = BLENDS.index(val.lower())
            except ValueError as e:
                raise SpecError(f"{name}:{n}: bad @{key} {val!r}") from e
            continue
        m = _UNIFORM.match(line)
        if not m:
            if "@param" in line:
                raise SpecError(f"{name}:{n}: @param needs 'uniform float|int u_name;' before it")
            continue
        typ, uniform, body = m.groups()
        pm = _PARAM.match(body + " ")
        if not pm:
            raise SpecError(f'{name}:{n}: @param wants lo hi default [log] [wrap] "Label" tip')
        lo, hi, default = (float(x) for x in pm["nums"].split())
        flags = pm["flags"].split()
        key = uniform[2:]
        if key in RESERVED or key in seen:
            raise SpecError(f"{name}:{n}: u_{key} — {key!r} is taken")
        if not lo < hi:
            raise SpecError(f"{name}:{n}: u_{key} needs lo < hi")
        if "log" in flags and lo <= 0:
            raise SpecError(f"{name}:{n}: u_{key} is log, so lo must be > 0")
        seen.add(key)
        spec.params.append(ParamSpec(
            key=key, uniform=uniform, label=pm["label"], lo=lo, hi=hi,
            default=min(max(default, lo), hi), integer=typ == "int", log="log" in flags,
            wrap="wrap" in flags, tip=pm["tip"].strip(),
        ))
    if not re.search(r"\bvec4\s+effect\s*\(", source):
        raise SpecError(f"{name}: no 'vec4 effect(vec2 uv)'")
    return spec


class FxState:
    """The fx.* params' object: the specs on disk, their values, their clocks.

    `values[name]` holds one effect's settings by key — its five own
    (on, mix, speed, blend, order) and one per annotated uniform. The dicts
    are kept across a reload of the file, so a value survives an edit that
    does not remove its uniform.
    """

    def __init__(self, directory: Path | str = FX_DIR):
        self.dir = Path(directory)
        self.on = True           # fx.on — the chain's bypass
        self.mix = 1.0           # fx.mix — scales every effect's mix
        self.sel = 0             # fx.select — the effect whose strip is open
        self.specs: dict[str, EffectSpec] = {}
        self.values: dict[str, dict[str, Any]] = {}
        self.phase: dict[str, float] = {}
        self.errors: dict[str, str] = {}       # file → why it is not loaded
        self.lib = ""                          # _lib.glsl's text
        # the registry's re-declare hook (params.py sets it): called with
        # the effect names whose params changed shape on a reload
        self.on_specs: Callable[[set[str]], None] | None = None
        self._mtimes: dict[str, float] = {}
        self.load()

    # ---- the folder ----

    def _scan(self) -> dict[str, float]:
        out = {}
        if self.dir.is_dir():
            for p in self.dir.glob("*.glsl"):
                try:
                    out[p.name] = p.stat().st_mtime
                except OSError:
                    pass
        return out

    def load(self) -> set[str]:
        """(Re)read the folder. Returns the effects whose declared params
        changed (added, removed, or re-shaped)."""
        mt = self._scan()
        self._mtimes = mt
        try:
            self.lib = (self.dir / LIB_FILE).read_text()
        except OSError:
            self.lib = ""
        changed: set[str] = set()
        found: dict[str, EffectSpec] = {}
        self.errors = {}
        for fname in sorted(mt):
            if fname.startswith("_"):
                continue
            name = fname[:-5]
            try:
                found[name] = parse(name, (self.dir / fname).read_text())
            except (OSError, SpecError) as e:
                self.errors[name] = str(e)
                if name in self.specs:        # a broken edit keeps the last good spec
                    found[name] = self.specs[name]
        for name in set(self.specs) - set(found):
            changed.add(name)
            self.values.pop(name, None)
            self.phase.pop(name, None)
        for name, spec in found.items():
            old = self.specs.get(name)
            if old is None or old.signature() != spec.signature():
                changed.add(name)
                self._adopt(spec)
        self.specs = found
        return changed

    def _adopt(self, spec: EffectSpec) -> None:
        """Values for a new or re-shaped spec: keep what still exists."""
        old = self.values.get(spec.name, {})
        v = {"on": bool(old.get("on", False)), "mix": float(old.get("mix", 1.0)),
             "speed": float(old.get("speed", spec.speed)),
             "blend": int(old.get("blend", spec.blend)),
             "order": int(old.get("order", spec.order))}
        for p in spec.params:
            x = old.get(p.key, p.default)
            v[p.key] = round(x) if p.integer else float(x)
        self.values[spec.name] = v
        self.phase.setdefault(spec.name, 0.0)

    def poll(self) -> set[str]:
        """Pick up edited, added and removed files; re-declare what changed."""
        if self._scan() == self._mtimes:
            return set()
        changed = self.load()
        if changed and self.on_specs is not None:
            self.on_specs(changed)
        return changed

    # ---- the chain ----

    def names(self) -> list[str]:
        """Every effect, in stack order."""
        return sorted(self.specs, key=lambda n: (self.values[n]["order"], n))

    def chain(self) -> list[str]:
        """The effects that run this frame, in order."""
        if not self.on or self.mix <= 0.0:
            return []
        return [n for n in self.names()
                if self.values[n]["on"] and self.values[n]["mix"] > 0.0]

    def selected(self) -> str | None:
        names = self.names()
        return names[max(0, min(self.sel, len(names) - 1))] if names else None

    def advance(self, dt: float) -> None:
        """Every effect's clock by dt at its speed — on or not, so an effect
        switched on mid-set is already moving."""
        for n, v in self.values.items():
            self.phase[n] = self.phase.get(n, 0.0) + dt * v["speed"]


def declare(r, fx: FxState, names: set[str] | None = None) -> None:
    """The fx.* params on registry `r`: everything, or with `names` just
    those effects' (a file changed shape on reload). Bindings to an id that
    goes away go dormant, as for a deleted band."""
    g = "fx"
    if names is None:
        r.remove_prefix("fx.")
        r.toggle("fx.on", "Effects", *_attr(fx, "on"), group=g,
                 tip="The effect stack's bypass: off, the frame goes straight to the "
                     "screen whatever is switched on below.")
        r.continuous("fx.mix", "FX mix", *_attr(fx, "mix"), lo=0.0, hi=1.0,
                     fmt=lambda v: f"mix {v:.2f}", group=g,
                     tip="Scales every effect's mix — one fader to fade the whole stack in.")
        r.enum("fx.select", "Edit", *_attr(fx, "sel"),
               lambda: [fx.specs[n].label for n in fx.names()], group=g,
               persist=False, modulatable=False,
               tip="Which effect's faders are open on the page.")
        names = set(fx.specs)
    for name in sorted(names):
        r.remove_prefix(f"fx.{name}.")
        spec = fx.specs.get(name)
        if spec is None:
            continue
        v = fx.values[name]
        pre, lb = f"fx.{name}", spec.label
        r.toggle(f"{pre}.on", lb, *_key(v, "on"), group=g, tip=spec.tip)
        r.continuous(f"{pre}.mix", f"{lb} mix", *_key(v, "mix"), lo=0.0, hi=1.0,
                     fmt=lambda x: f"mix {x:.2f}", group=g,
                     tip="Wet/dry: 0 its input untouched, 1 the effect in full.")
        r.continuous(f"{pre}.speed", f"{lb} speed", *_key(v, "speed"),
                     lo=-SPEED_MAX, hi=SPEED_MAX, fmt=lambda x: f"{x:+.2f}×", group=g,
                     tip="The rate of the effect's clock; negative runs it backwards, 0 "
                         "freezes it.")
        r.enum(f"{pre}.blend", f"{lb} blend", *_key(v, "blend"), BLENDS, group=g,
               tip="How the effect's output lands on its input: mix replaces, add and "
                   "screen light up, multiply darkens.")
        r.continuous(f"{pre}.order", f"{lb} order", *_key(v, "order"), lo=0, hi=MAX_ORDER,
                     integer=True, fmt=lambda x: f"#{int(x)}", group=g, modulatable=False,
                     tip="Where it sits in the stack: low runs first, so a warp before a "
                         "colour pass bends the colour too.")
        for p in spec.params:
            r.continuous(f"{pre}.{p.key}", f"{lb} {p.label.lower()}", *_key(v, p.key),
                         lo=p.lo, hi=p.hi, log=p.log, wrap=p.wrap, integer=p.integer,
                         fmt=_fmt(p), group=g, tip=p.tip)


def _attr(obj, name):
    return (lambda: getattr(obj, name)), (lambda x: setattr(obj, name, x))


def _key(d: dict, k: str):
    return (lambda: d[k]), (lambda x: d.__setitem__(k, x))


def _fmt(p: ParamSpec) -> Callable[[float], str]:
    if p.integer:
        return lambda x: f"{int(x)}"
    span = p.hi - p.lo
    digits = 3 if span <= 0.2 else 2 if span <= 20 else 1 if span <= 200 else 0
    return lambda x: f"{x:.{digits}f}"


# ---- GL ----

QUAD_VS = """
#version 330
out vec2 v_uv;
void main() {
    vec2 p = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
    v_uv = p;
    gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
}
"""

# every effect is compiled inside this: the lib (string 1) and the effect
# file (string 2) — #line makes a compile error name the file's own line
FS_HEAD = """#version 330
uniform sampler2D u_src;   // the frame so far
uniform vec2 u_res;        // its size, px
uniform float u_phase;     // the effect's clock: seconds × its speed
uniform float u_time;      // seconds, wall clock
uniform float u_mix;       // its mix × fx.mix
uniform int u_blend;       // index into BLENDS
in vec2 v_uv;
out vec4 f_color;
"""

FS_TAIL = """
void main() {
    vec4 a = texture(u_src, v_uv);
    vec4 b = effect(v_uv);
    vec4 c = u_blend == 1 ? a + b
           : u_blend == 2 ? a + b - a * b
           : u_blend == 3 ? a * b
           : b;
    c = clamp(mix(a, c, u_mix), 0.0, 1.0);
    // premultiplied: a pass that lights a pixel also covers it
    c.a = max(c.a, max(c.r, max(c.g, c.b)));
    f_color = c;
}
"""

COPY_FS = """
#version 330
uniform sampler2D u_src;
in vec2 v_uv;
out vec4 f_color;
void main() { f_color = texture(u_src, v_uv); }
"""


def fragment_source(lib: str, effect: str) -> str:
    return f"{FS_HEAD}#line 1 1\n{lib}\n#line 1 2\n{effect}\n#line 1 3\n{FS_TAIL}"


def _gl_error(e: Exception) -> str:
    """The first compiler message, with its file named."""
    lines = [ln.strip() for ln in str(e).splitlines() if ln.strip()]
    msg = next((ln for ln in lines if "ERROR" in ln.upper()), lines[-1] if lines else str(e))
    msg = re.sub(r"ERROR:\s*1:(\d+):", r"_lib.glsl:\1:", msg)
    msg = re.sub(r"ERROR:\s*2:(\d+):", r"line \1:", msg)
    return msg[:200]


class FxChain:
    """The ping-pong textures and one program per effect, on one GL context."""

    def __init__(self, ctx: moderngl.Context, state: FxState | None = None):
        self.ctx = ctx
        self.state = state if state is not None else FxState()
        self.size = (0, 0)
        self._tex: list[moderngl.Texture] = []
        self._fbo: list[moderngl.Framebuffer] = []
        # name → (source it was built from, program, vao); a failed build
        # keeps the last good entry and records why in `errors`
        self._progs: dict[str, tuple[str, moderngl.Program, moderngl.VertexArray]] = {}
        self._tried: dict[str, str] = {}        # name → source of the last attempt
        self.errors: dict[str, str] = {}
        self._t_last: float | None = None
        self._t0 = time.perf_counter()
        self._frame = 0
        self._build_copy()

    def _build_copy(self) -> None:
        self._copy = self.ctx.program(vertex_shader=QUAD_VS, fragment_shader=COPY_FS)
        self._copy_vao = self.ctx.vertex_array(self._copy, [])
        self._copy["u_src"].value = 0

    def on_reload(self) -> None:
        """Hot-swap hook: every program is rebuilt from source on next use."""
        for _, prog, vao in self._progs.values():
            vao.release()
            prog.release()
        self._progs.clear()
        self._tried.clear()
        self._copy_vao.release()
        self._copy.release()
        self._build_copy()

    # ---- per frame ----

    def tick(self) -> None:
        """Once a frame, on or off: watch the folder every RELOAD_EVERY frames."""
        self._frame += 1
        if self._frame % RELOAD_EVERY == 0:
            self.state.poll()

    def active(self) -> bool:
        return bool(self.state.chain())

    def begin(self, size: tuple[int, int]) -> moderngl.Framebuffer:
        """The framebuffer the frame should be composited into this frame."""
        if size != self.size or not self._tex:
            self.release_targets()
            self.size = size
            for _ in range(2):
                tex = self.ctx.texture(size, 4, dtype="f2")
                tex.repeat_x = tex.repeat_y = False
                self._tex.append(tex)
                self._fbo.append(self.ctx.framebuffer(color_attachments=[tex]))
        return self._fbo[0]

    def release_targets(self) -> None:
        for res in (*self._fbo, *self._tex):
            res.release()
        self._fbo, self._tex = [], []
        self.size = (0, 0)

    def run(self, target: moderngl.Framebuffer, t_now: float | None = None) -> list[str]:
        """Every active effect over the frame `begin()` handed out, the last
        one into `target`'s viewport. Returns the effects that ran.

        `t_now` pins the clock (offscreen renders); otherwise it is the
        wall clock. Effects advance by the time since the previous run."""
        st = self.state
        t = t_now if t_now is not None else time.perf_counter() - self._t0
        dt = 0.0 if self._t_last is None else max(0.0, min(t - self._t_last, 0.25))
        self._t_last = t
        st.advance(dt)
        passes = [(n, self._program(n)) for n in st.chain()]
        passes = [(n, pv) for n, pv in passes if pv is not None]
        ctx = self.ctx
        ctx.disable(moderngl.BLEND)
        w, h = self.size
        src = 0
        if not passes:                 # everything on failed to build: a copy
            target.use()
            self._tex[0].use(location=0)
            self._copy_vao.render(moderngl.TRIANGLES, vertices=3)
        for k, (name, (prog, vao)) in enumerate(passes):
            last = k == len(passes) - 1
            (target if last else self._fbo[1 - src]).use()
            self._tex[src].use(location=0)
            v = st.values[name]
            self._set(prog, "u_src", 0)
            self._set(prog, "u_res", (float(w), float(h)))
            self._set(prog, "u_phase", float(st.phase.get(name, 0.0)))
            self._set(prog, "u_time", float(t))
            self._set(prog, "u_mix", float(v["mix"]) * float(st.mix))
            self._set(prog, "u_blend", int(v["blend"]))
            for p in st.specs[name].params:
                x = v[p.key]
                self._set(prog, p.uniform, round(x) if p.integer else float(x))
            vao.render(moderngl.TRIANGLES, vertices=3)
            src = 1 - src
        ctx.enable(moderngl.BLEND)
        return [n for n, _ in passes]

    @staticmethod
    def _set(prog: moderngl.Program, name: str, value) -> None:
        # the driver drops a uniform the effect never reads
        if name in prog:
            prog[name].value = value

    def _program(self, name: str):
        """The effect's (program, vao), built on first use and on every
        change to its file or the lib; None if it never compiled."""
        st = self.state
        spec = st.specs.get(name)
        if spec is None:
            return None
        src = fragment_source(st.lib, spec.source)
        have = self._progs.get(name)
        if (have is None or have[0] != src) and self._tried.get(name) != src:
            self._tried[name] = src
            try:
                prog = self.ctx.program(vertex_shader=QUAD_VS, fragment_shader=src)
            except Exception as e:  # noqa: BLE001 — a bad edit must not kill the show
                self.errors[name] = _gl_error(e)
            else:
                if have is not None:
                    have[2].release()
                    have[1].release()
                self._progs[name] = have = (src, prog, self.ctx.vertex_array(prog, []))
                self.errors.pop(name, None)
        return None if have is None else (have[1], have[2])

    def compile_all(self) -> dict[str, str]:
        """Build every effect now (tests, tools); returns name → error."""
        for n in self.state.specs:
            self._program(n)
        return dict(self.errors)

    def error(self, name: str) -> str:
        """Why an effect is not what its file says: parse, then compile."""
        return self.state.errors.get(name) or self.errors.get(name, "")
