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
without its ``u_`` is the id suffix. Every effect also gets six params
of its own: ``on``, ``mix`` (wet/dry against its input), ``speed`` (the
rate its clock ``u_phase`` runs at — integrated here, so a lane riding
the speed never jumps the phase), ``blend``, ``order`` and ``target``.
Three more are the stack's: ``fx.on`` (bypass everything), ``fx.mix``
(scales every effect's mix — one fader that fades the whole trip in) and
``fx.face_map`` (below).

An effect is aimed at one of two targets (plan 20): the **frame**, as
below, or the **faces** — the effects aimed there run as a second chain
over a fixed-size picture of what a face shows, and the face shader draws
that picture on every face (render.py, ``Renderer._face_picture``),
mapped per face or in screen space (``fx.face_map``). The two chains are
two ``FxChain`` s over one ``FxState``: the second borrows the first's
programs (one compile and one error line per effect), and the clocks
advance once a frame whichever runs (``FxState.advance_to``).

The frame (render.py): the scene is drawn, the look-back composites it
into the first of two ping-pong textures instead of the window, each
active effect reads one and writes the other, and the last writes the
window. With no effect on the chain is not in the path at all and the
output is bit-identical to before. The look-back captures the scene, not
the effected frame, so echoes are never warped twice.

Colour stays premultiplied (overlay.py clears to see-through): after its
blend a pass lifts alpha to cover its own colour, so a generator painting
over a transparent ground shows on the desktop. On an opaque ground
(window and fullscreen, ``FxChain.opaque``, set by the renderer each
frame) every pass writes alpha 1, whatever its blend — a multiply or an
effect returning a low alpha never lets the desktop through (plan 14 WP1).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import moderngl

from .glsl import QUAD_VS, common, common_mtime, gl_error

FX_DIR = Path(__file__).parent / "shaders" / "fx"
LIB_FILE = "_lib.glsl"          # helpers prepended to every effect; not an effect
BLENDS = ["mix", "add", "screen", "multiply"]
TARGETS = ["frame", "faces"]    # fx.<name>.target's choices: what an effect runs on
FRAME, FACES = 0, 1
FACE_MAPS = ["per face", "screen"]   # fx.face_map's choices: how the faces show their picture
PER_FACE, SCREEN = 0, 1
RESERVED = {"on", "mix", "speed", "blend", "order", "target"}   # the per-effect params' names
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

    `values[name]` holds one effect's settings by key — its six own
    (on, mix, speed, blend, order, target) and one per annotated uniform. The dicts
    are kept across a reload of the file, so a value survives an edit that
    does not remove its uniform.
    """

    def __init__(self, directory: Path | str = FX_DIR):
        self.dir = Path(directory)
        self.on = True           # fx.on — the chain's bypass
        self.mix = 1.0           # fx.mix — scales every effect's mix
        self.face_map = PER_FACE # fx.face_map — how the faces show their effects' picture
        self._t_last: float | None = None      # the frame time of the last advance_to
        # the open strip's effect, by name (None: whatever is first). A name,
        # not an index into names(): a reorder or a preset load never moves it
        self.sel_name: str | None = None
        self.specs: dict[str, EffectSpec] = {}
        self.values: dict[str, dict[str, Any]] = {}
        self.phase: dict[str, float] = {}
        self.errors: dict[str, str] = {}       # file → why it is not loaded
        self.lib = ""                          # _lib.glsl's text
        self.common = ""                       # shaders/_common.glsl's text
        # the registry's re-declare hook (params.py sets it): called with
        # the effect names whose params changed shape on a reload
        self.on_specs: Callable[[set[str]], None] | None = None
        self._mtimes: dict[str, float] = {}
        self.load()

    # ---- the folder ----

    def _scan(self) -> dict[str, float]:
        out = {"_common": common_mtime()}      # the shared helpers count as a change too
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
        self.common = common()
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
             "order": int(old.get("order", spec.order)),
             "target": int(old.get("target", FRAME))}
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

    def chain(self, target: int | None = None) -> list[str]:
        """The effects that run this frame, in order: all of them, or with
        `target` (FRAME, FACES) only those aimed at it."""
        if not self.on or self.mix <= 0.0:
            return []
        return [n for n in self.names()
                if self.values[n]["on"] and self.values[n]["mix"] > 0.0
                and (target is None or _target(self.values[n]) == target)]

    def select(self, name: str | None) -> None:
        """Open `name`'s strip. A name with no spec is ignored; None means
        'whatever is first'. Writes nothing but sel_name."""
        if name is None or name in self.specs:
            self.sel_name = name

    def selected(self) -> str | None:
        """sel_name while it has a spec; else the first of names(); None
        with no effects. Never writes — a file that goes away and comes
        back is open again."""
        # getattr: a hot reload re-classes the live FxState without running
        # __init__ (hotreload.py), so an instance from before has no sel_name
        name = getattr(self, "sel_name", None)
        if name in self.specs:
            return name
        names = self.names()
        return names[0] if names else None

    def advance(self, dt: float) -> None:
        """Every effect's clock by dt at its speed — on or not, so an effect
        switched on mid-set is already moving."""
        for n, v in self.values.items():
            self.phase[n] = self.phase.get(n, 0.0) + dt * v["speed"]

    def advance_to(self, t: float) -> float:
        """Every effect's clock up to the frame time `t`: advance(dt) with
        dt the time since the last call, clamped to 0…0.25 s, 0 on the
        first. A second call with the same `t` advances nothing — two
        chains run over one state in a frame (the frame's and the faces'),
        and whichever runs first moves the clocks. Returns the dt applied."""
        # getattr: an FxState from before a hot reload has no _t_last
        last = getattr(self, "_t_last", None)
        dt = 0.0 if last is None else max(0.0, min(t - last, 0.25))
        self._t_last = t
        self.advance(dt)
        return dt


def _target(v: dict) -> int:
    """An effect's target from its values: FRAME for anything but FACES (a
    dict from before a hot reload has no key, and a stray value must not
    lose the effect from both chains)."""
    return FACES if v.get("target", FRAME) == FACES else FRAME


def reordered(seq: list[str], orders: dict[str, int], moved: str) -> dict[str, int]:
    """Orders (0…MAX_ORDER) under which sorting by (order, name) gives
    `seq`, changing as few effects as possible: `moved` alone when it can
    be done, else the smallest run of neighbours that can. Returns only
    the effects whose order changes.

    `seq` is `names()` with `moved` taken out and put back somewhere (a
    chip dragged on the FX page, plan 20 WP3); `orders` is every effect's
    order now. Pure: it reads nothing but its arguments.

    One run of `seq` is renumbered: the shortest whose two sides already
    sort as `seq` has them and which has room — as many integers strictly
    between the orders either side of it as it has effects. It gets those
    integers evenly spaced (one effect alone: the middle of its gap). So
    no tie is ever made or relied on, and the name tie-break in `names()`
    cannot reorder the result; a tie that is already there and not in the
    way is left alone. Of two runs of one length, one holding `moved` is
    taken, then the one further right: the same drop always gives the
    same orders. With no room for a short run the run grows, to the whole
    list at worst (0…99: up to a hundred effects; past that orders repeat)."""
    def key(k: int) -> tuple[int, str]:
        return orders[seq[k]], seq[k]
    n = len(seq)
    bad = [k for k in range(1, n) if not key(k - 1) < key(k)]    # seq[k] is out of place
    if not bad:
        return {}                                    # it already sorts that way
    first, last = bad[0], bad[-1]                    # seq[:first] and seq[last:] sort as they are
    i = seq.index(moved)
    for size in range(max(1, last - first), n + 1):
        los = range(min(first, n - size), max(0, last - size) - 1, -1)
        for lo in sorted(los, key=lambda lo: not lo <= i < lo + size):   # stable: right first
            hi = lo + size                           # the run is seq[lo:hi]
            a = orders[seq[lo - 1]] if lo > 0 else -1
            b = orders[seq[hi]] if hi < n else MAX_ORDER + 1
            free = b - a - 1                         # the integers strictly between
            if free < size and size != n:            # no room; the whole list is the last resort
                continue
            if size == 1:
                new = [(a + b) // 2]                 # the middle of the gap
            else:                                    # evenly through the gap, in seq's order
                new = [min(a + 1 + ((2 * j + 1) * free) // (2 * size), MAX_ORDER)
                       for j in range(size)]
            return {name: o for name, o in zip(seq[lo:hi], new, strict=True)
                    if o != orders[name]}
    return {}


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
        r.enum("fx.face_map", "Faces show", lambda: getattr(fx, "face_map", PER_FACE),
               lambda x: setattr(fx, "face_map", x), FACE_MAPS, group=g,
               tip="How the faces' effects sit on the shape: per face, every face carries "
                   "the whole picture and it turns with the shape; screen, the faces are "
                   "windows onto one picture that stays still while the shape moves "
                   "across it.")
        # a view onto FxState.sel_name: it reads the open effect's place in
        # the stack, and a write opens the effect at that place. The name is
        # what is kept, so the index follows the effect when the order moves
        r.enum("fx.select", "Edit", lambda: _sel_index(fx), lambda i: _sel_set(fx, i),
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
        # where it runs: the stack's structure, like order — set, never ridden
        r.enum(f"{pre}.target", f"{lb} target", lambda v=v: v.get("target", FRAME),
               lambda x, v=v: v.__setitem__("target", x), TARGETS, group=g,
               modulatable=False,
               tip="What the effect runs on: the whole frame, or the picture in the "
                   "faces (Faces must be on).")
        for p in spec.params:
            r.continuous(f"{pre}.{p.key}", f"{lb} {p.label.lower()}", *_key(v, p.key),
                         lo=p.lo, hi=p.hi, log=p.log, wrap=p.wrap, integer=p.integer,
                         fmt=_fmt(p), group=g, tip=p.tip)


def _sel_index(fx: FxState) -> int:
    """fx.select's value: where the open effect sits in names(); 0 with none."""
    names = fx.names()               # sorted once: this is read by every surface that shows it
    name = getattr(fx, "sel_name", None)
    return names.index(name) if name in fx.specs else 0


def _sel_set(fx: FxState, i) -> None:
    """A write to fx.select: open the effect at `i` in names(), clamped."""
    names = fx.names()
    if names:
        fx.select(names[max(0, min(int(i), len(names) - 1))])


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

# every effect is compiled inside this: the shared helpers (string 1,
# shaders/_common.glsl), the lib (string 2) and the effect file (string 3)
# — #line makes a compile error name the file's own line
FS_HEAD = """#version 330
uniform sampler2D u_src;   // the frame so far
uniform vec2 u_res;        // its size, px
uniform float u_phase;     // the effect's clock: seconds × its speed
uniform float u_time;      // seconds, wall clock
uniform float u_mix;       // its mix × fx.mix
uniform int u_blend;       // index into BLENDS
uniform int u_opaque;      // 1 on an opaque ground (window, fullscreen): alpha stays 1
                           // (always 0 on the faces' chain: there alpha is a face's intensity)
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
    // on an opaque ground nothing may let the desktop through (plan 14 WP1)
    if (u_opaque != 0) c.a = 1.0;
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


def fragment_source(lib: str, effect: str, shared: str | None = None) -> str:
    shared = common() if shared is None else shared
    return (f"{FS_HEAD}#line 1 1\n{shared}\n#line 1 2\n{lib}\n#line 1 3\n{effect}\n"
            f"#line 1 4\n{FS_TAIL}")


class FxChain:
    """The ping-pong textures and one program per effect, on one GL context.

    A chain runs the effects aimed at its `target`: the frame's (the
    default — with every effect aimed at the frame it is the whole stack)
    or the faces'. A chain made with `programs=` another chain borrows that
    chain's programs and speaks its errors: one compile per effect and one
    error line however many chains run it. Every uniform is set before
    each pass, so one program serves two chains in a frame."""

    def __init__(self, ctx: moderngl.Context, state: FxState | None = None, *,
                 target: int = FRAME, programs: FxChain | None = None):
        self.ctx = ctx
        self.state = state if state is not None else FxState()
        self.target = target
        self.programs = programs        # the chain whose programs this one runs; None: its own
        self.size = (0, 0)
        self._tex: list[moderngl.Texture] = []
        self._fbo: list[moderngl.Framebuffer] = []
        # name → (source it was built from, program, vao); a failed build
        # keeps the last good entry and records why in `errors`
        self._progs: dict[str, tuple[str, moderngl.Program, moderngl.VertexArray]] = {}
        self._tried: dict[str, str] = {}        # name → source of the last attempt
        # a borrower's errors are the owner's dict: one line for both targets
        self.errors: dict[str, str] = {} if programs is None else programs.errors
        self._frame = 0
        self.opaque = False     # the ground is opaque: every pass writes alpha 1 (Renderer.draw)
        self._build_copy()

    def _build_copy(self) -> None:
        self._copy = self.ctx.program(vertex_shader=QUAD_VS, fragment_shader=COPY_FS)
        self._copy_vao = self.ctx.vertex_array(self._copy, [])
        self._copy["u_src"].value = 0

    def on_reload(self) -> None:
        """Hot-swap hook: every program is rebuilt from source on next use.
        A borrower holds none: only the owner releases programs."""
        self._release_programs()
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
        # getattr: a chain from before a hot reload has no target
        return bool(self.state.chain(getattr(self, "target", FRAME)))

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

    def release(self) -> None:
        """Everything this chain made on the GL context: its textures, its
        copy program and — unless it borrows them — its effect programs."""
        self.release_targets()
        self._release_programs()
        self._copy_vao.release()
        self._copy.release()

    def _release_programs(self) -> None:
        """This chain's own effect programs (a borrower has none)."""
        for _, prog, vao in self._progs.values():
            vao.release()
            prog.release()
        self._progs.clear()
        self._tried.clear()

    def run(self, target: moderngl.Framebuffer, t: float) -> list[str]:
        """Every active effect over the frame `begin()` handed out, the last
        one into `target`'s viewport. Returns the effects that ran.

        `t` is the frame's time in seconds — the renderer's one clock
        (Renderer.draw), pinned by callers that render offscreen. Effects
        advance by the time since the state's clocks last moved: once a
        frame, whichever chain runs first (FxState.advance_to)."""
        st = self.state
        st.advance_to(t)
        aim = getattr(self, "target", FRAME)
        # in the faces' picture alpha is a face's intensity, never the window's
        opaque = int(aim == FRAME and getattr(self, "opaque", False))
        passes = [(n, self._program(n)) for n in st.chain(aim)]
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
            self._set(prog, "u_opaque", opaque)
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
        change to its file or the lib; None if it never compiled. A
        borrower asks the chain it borrows from."""
        owner = getattr(self, "programs", None)
        if owner is not None:
            return owner._program(name)
        st = self.state
        spec = st.specs.get(name)
        if spec is None:
            return None
        src = fragment_source(st.lib, spec.source, st.common)
        have = self._progs.get(name)
        if (have is None or have[0] != src) and self._tried.get(name) != src:
            self._tried[name] = src
            try:
                prog = self.ctx.program(vertex_shader=QUAD_VS, fragment_shader=src)
            except Exception as e:  # noqa: BLE001 — a bad edit must not kill the show
                self.errors[name] = gl_error(e, {1: "_common.glsl:", 2: "_lib.glsl:", 3: "line "})
            else:
                if have is not None:
                    have[2].release()
                    have[1].release()
                self._progs[name] = have = (src, prog, self.ctx.vertex_array(prog, []))
                self.errors.pop(name, None)
        return None if have is None else (have[1], have[2])

    def compile_all(self) -> dict[str, str]:
        """Build every effect now (tests, tools); returns name → error."""
        owner = getattr(self, "programs", None)
        if owner is not None:
            return owner.compile_all()
        for n in self.state.specs:
            self._program(n)
        return dict(self.errors)

    def error(self, name: str) -> str:
        """Why an effect is not what its file says: parse, then compile."""
        return self.state.errors.get(name) or self.errors.get(name, "")
