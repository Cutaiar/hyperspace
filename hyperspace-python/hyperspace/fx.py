"""Effects — fullscreen shader passes, each where the graph wires it.

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
    // @order  20                   read only by the migration (below)
    // @blend  mix                  mix | add | screen | multiply — how its
                                    output lands on its input
    // @speed  1                    the default time rate
    // @mix    1                    the default wet/dry (0: starts as a no-op)
    // @tip    …                    one line for the tooltip
    uniform float u_amount;  // @param 0 2 0.5 "Amount" tooltip text…
    uniform float u_scale;   // @param 0.5 12 3 log "Scale" …
    uniform int   u_count;   // @param 2 16 6 "Count" …    (int uniform → integer param)
    vec4 effect(vec2 uv) { return src(uv + …); }

``@param lo hi default [log] [wrap] [amount] "Label" tip`` — the uniform
name without its ``u_`` is the id suffix. ``amount`` (wave 0 T1) marks a
param whose range is 0 … hi with a meaningful zero — how much of the
effect there is — and puts it on the zero-safe log taper
(`amount_taper`: position 0 is off, then ten doublings up to hi), so a
knob reaches 0.05 of the range as easily as 0.5; it needs ``lo`` 0, a
float uniform, and neither ``log`` nor ``wrap``. A discrete choice (plan 30 N8) is
``uniform int u_mode; // @param choice [compress|gradient] 0 "Mode" tip``:
the names in brackets, ``|`` between them, then the default's index — an
enum param the strips draw as a picker (a combo), never a slider; the
uniform gets the index. Every effect also gets four params
of its own: ``on``, ``mix`` (wet/dry against its input), ``speed`` (the
rate its clock ``u_phase`` runs at — integrated here, so a lane riding
the speed never jumps the phase; on the signed exponential taper
`T_SPEED`, stop in the middle, ±8× at the ends) and ``blend``. Three more are every
effect's: ``fx.on`` (bypass everything), ``fx.mix`` (scales every
effect's mix — one fader that fades the whole trip in) and
``fx.face_map`` (how the faces show a picture wired into them).

**No shader multiplies time by a param** (the owner, 2026-11-02, after
the show of 2026-10-30: ``u_phase * u_drift`` shifts the field by
``phase × Δdrift`` — whole screens, hours into a set — on one knob step).
A rate-like param is integrated here and the shader reads the phase::

    // @clock u_drift_t drift          a second clock: u_drift_t += speed × drift × dt
    // @clock u_pulse_t pulse tau      …wrapped to 2π (any period > 0, or `tau`)
    // @clock u_cells_t drift*scale    a product of params: speed × drift × scale × dt

``@clock <uniform> <rate-param>[*<rate-param>…] [period]``: the uniform (``u_…``, one
the file does not declare — this module does, beside ``u_phase``) is a
phase this module integrates every frame, ``speed × <rate-param> × dt``
(the rate is one of the file's own ``@param`` keys, and the effect's
speed fader still scales it, as it scaled ``u_phase``), so while the knob
is still ``u_drift_t`` equals today's ``u_phase * u_drift``, and when the
knob moves only the rate changes, never where the field is. With a
period the phase is kept in ``[0, period)``, for a shader that reads it
through ``sin`` or ``fract``; without one it runs on like ``u_phase``
(a scrolled noise field has no period to wrap to). A rate may be a
product of the file's params (``drift*scale``, each once): warp counts
its scroll in noise cells, so the cells a second are drift × scale and a
scale step re-zooms the cells about the centre without sliding them
(K2, register row 577). The phases live on
``FxState.clocks`` and survive a hot reload of this module as the speed
phases do; ``tests/test_shader_time_lint.py`` holds every shipped shader
to the rule.

Plan 33 (rows 341–349): an effect exists where the preset's graph wires
it — the run ``frame → … → fx.image`` each pipeline draws, a branch onto
the faces (``shape.faces``), the pattern's layer, the backdrop, an output
or another effect's ``aux`` — and nowhere else. There is no stack: no
``order`` and no ``target`` param (an old preset's are read as wires by
``graphmigrate``, which is all a file's ``@order`` is still for), and the
render graph runs each effect as a node (``graph.Effect``: one pass,
``FxChain.run_one``). With no effect wired the frame is bit-identical to
before. The look-back captures the scene, not the effected frame, so
echoes are never warped twice.

Colour stays premultiplied (overlay.py clears to see-through): after its
blend a pass lifts alpha to cover its own colour, so a generator painting
over a transparent ground shows on the desktop. On an opaque ground
(window and fullscreen, ``FxChain.opaque``, set by the renderer each
frame) every pass writes alpha 1, whatever its blend — a multiply or an
effect returning a low alpha never lets the desktop through (plan 14 WP1).
"""

from __future__ import annotations

import functools
import math
import re
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import moderngl

from . import tapers
from .glsl import QUAD_VS, common, common_mtime, gl_error

FX_DIR = Path(__file__).parent / "shaders" / "fx"
LIB_FILE = "_lib.glsl"          # helpers prepended to every effect; not an effect
BLENDS = ["mix", "add", "screen", "multiply"]
FACE_MAPS = ["per face", "screen"]   # fx.face_map's choices: how the faces show their picture
PER_FACE, SCREEN = 0, 1
# the per-effect params' names — and `order` / `target`, retired (plan 33)
# but still in old presets as `fx.<n>.order`: a uniform of either name
# would read as the retired id, so neither is ever a key
RESERVED = {"on", "mix", "speed", "blend", "order", "target"}
SPEED_MAX = 8.0
# wave 0 T1 (the owner, 2026-10-31: "turning those values down to 0.05× or
# 5 % … very, very low values are really convincing"): a knob on a linear
# −8 … +8 could not reach 0.05× (0.003 of its throw, under one MIDI step),
# so `speed` is on a signed exponential taper: 401 detents, the stop in the
# middle, 1× at 140 steps out (20 a doubling), ±8× at the ends and
# ±2^(−6.95) ≈ ±0.008× one step from the stop — ten octaves a side, so
# 0.05× sits at detent 254, a third of the way up the positive side
SPEED_SIDE, SPEED_UNITY = 200, 140
T_SPEED = tapers.exp_signed(SPEED_UNITY, SPEED_SIDE)
# an `amount` param's taper (`ParamSpec.amount`): off at 0, then ten
# doublings (200 detents) up to its hi — about hi / 1000 one step up
AMOUNT_OCTAVES = 10
RELOAD_EVERY = 30               # frames between mtime checks of the folder

_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
_DIRECTIVE = re.compile(r"^\s*//\s*@(label|order|blend|speed|mix|tip|clock)\s+(.*?)\s*$")
_CLOCK_UNIFORM = re.compile(r"^u_[a-z][a-z0-9_]*$")
_UNIFORM = re.compile(r"^\s*uniform\s+(float|int)\s+(u_\w+)\s*;\s*//\s*@param\s+(.*?)\s*$")
_CHOICE = re.compile(
    r"^choice\s+\[(?P<names>[^\]]*)\]\s+(?P<default>\d+)\s+\"(?P<label>[^\"]+)\"\s*(?P<tip>.*)$"
)
_PARAM = re.compile(
    r"^(?P<nums>(?:[-+]?[\d.]+(?:[eE][-+]?\d+)?\s+){3})"
    r"(?P<flags>(?:(?:log|wrap|amount)\s+)*)\"(?P<label>[^\"]+)\"\s*(?P<tip>.*)$"
)


class SpecError(ValueError):
    pass


def instance_of_name(name: str) -> int | None:
    """The instance number an effect name carries (plan 26 A4: `acid.2` →
    2, the naming rule's marker), or None for a file's own name (`acid`,
    instance 1)."""
    _, dot, mark = name.partition(".")
    return int(mark) if dot and mark.isdecimal() and int(mark) >= 2 else None


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
    choices: tuple[str, ...] = ()   # a discrete choice's names (`@param choice`): an enum
    amount: bool = False            # 0 … hi on the zero-safe log taper (wave 0 T1)


@dataclass(frozen=True)
class ClockSpec:
    """One `@clock` line: a phase this module integrates and binds."""

    uniform: str            # the uniform the shader reads (`u_…`), declared by this module
    rate: str               # the @param key whose value is the rate, × the effect's speed;
                            # `a*b`: the product of two (or more) of the file's params,
                            # sorted once checked, so one clock has one spelling
    period: float | None    # wrap to [0, period); None runs on like u_phase
    # the rate's @param keys, sorted — set by `_check_clocks` (the grammar
    # lives there), read every frame by `clock_rate`; () on a spec built by
    # hand or before a hot reload, which `clock_rate` splits for itself
    factors: tuple[str, ...] = field(default=(), compare=False)


@dataclass
class EffectSpec:
    """One effect file, parsed."""

    name: str
    label: str
    source: str
    params: list[ParamSpec] = field(default_factory=list)
    # `@order`: no part in anything drawn (plan 33) — the stack position an
    # old preset naming none had, which `graphmigrate` reads it as
    order: int = 50
    blend: int = 0
    speed: float = 1.0
    mix: float = 1.0         # the default wet/dry (@mix); 0 for a pass that starts as a no-op
    tip: str = ""
    clocks: list[ClockSpec] = field(default_factory=list)   # `@clock` lines, in file order

    def signature(self) -> tuple:
        """What the registry declares from this spec — a change means re-declare."""
        return (self.label, self.tip, self.order, self.blend, self.speed, self.mix,
                tuple((p.key, p.label, p.lo, p.hi, p.default, p.integer, p.log, p.wrap, p.tip,
                       p.choices, p.amount)
                      for p in self.params),
                tuple((c.uniform, c.rate, c.period) for c in getattr(self, "clocks", ())))


def clock_rate(clock: ClockSpec, values: dict[str, Any]) -> float:
    """A `@clock`'s rate from an effect's values: the product of its
    factors, a factor the values lack read as 0 (a stilled clock, never an
    exception on the frame). `FxState.advance` and the continuity harness
    both read it here. The checked spec's `factors`; a ClockSpec from
    before a hot reload of this module (or built by hand) has none, and
    its rate is split here."""
    rate = 1.0
    for k in getattr(clock, "factors", None) or clock.rate.split("*"):
        rate *= float(values.get(k, 0.0))
    return rate


def _check_key(name: str, n: int, key: str, seen: set[str]) -> None:
    if key in RESERVED or key in seen:
        raise SpecError(f"{name}:{n}: u_{key} — {key!r} is taken")
    if key.isdecimal():
        # the naming rule (plan 26 A0/A4): a purely decimal segment
        # right after `fx.<file>` is an instance marker — `fx.acid.2`
        # is the second acid — so no key may be one
        raise SpecError(f"{name}:{n}: u_{key} — a key of digits alone would read as an "
                        "instance number (fx.<file>.2 is the second instance)")


def _is_period(word: str) -> bool:
    """`tau` or a number: a period's word, never a rate's factor."""
    if word.lower() == "tau":
        return True
    try:
        float(word)
    except ValueError:
        return False
    return True


def _rate_word(words: list[str]) -> list[str]:
    """A `@clock` line's words with its rate made one word: a product may
    be written with spaces round its `*`s (`drift * scale`), so the words
    after the uniform are joined while one ends or the next starts with
    `*` — but never onto a period's word, so `drift * tau` (a dropped
    factor) stays `drift*` and is refused as an empty factor."""
    if len(words) < 2:
        return words
    rate, i = words[1], 2
    while (i < len(words) and (rate.endswith("*") or words[i].startswith("*"))
           and not _is_period(words[i])):
        rate += words[i]
        i += 1
    return [words[0], rate, *words[i:]]


def _parse_clock(name: str, n: int, val: str) -> ClockSpec:
    """`@clock <uniform> <rate-param>[*<rate-param>…] [period]` → its spec,
    the rate still to be checked against the file's params (`_check_clocks`)."""
    words = _rate_word(val.split())
    if len(words) not in (2, 3):
        raise SpecError(f"{name}:{n}: @clock wants <u_uniform> "
                        "<rate-param>[*<rate-param>…] [period]")
    uniform, rate = words[0], words[1]
    if not _CLOCK_UNIFORM.match(uniform):
        raise SpecError(f"{name}:{n}: @clock {uniform} — a clock's uniform is u_lower_snake")
    if uniform in HEAD_UNIFORMS:
        raise SpecError(f"{name}:{n}: @clock {uniform} — every effect already has it")
    period: float | None = None
    if len(words) == 3:
        word = words[2].lower()
        try:
            period = math.tau if word == "tau" else float(word)
        except ValueError as e:
            raise SpecError(f"{name}:{n}: @clock {uniform} — bad period {words[2]!r}") from e
        if not math.isfinite(period):       # `x %= inf` is inf for a backwards rate
            raise SpecError(f"{name}:{n}: @clock {uniform} — a period is finite and > 0 (or `tau`)")
        if not period > 0.0:
            raise SpecError(f"{name}:{n}: @clock {uniform} — a period is > 0 (or `tau`)")
    # the rate as written: a key, or a uniform — resolved against the
    # file's params once they are all read (`_check_clocks`)
    return ClockSpec(uniform=uniform, rate=rate, period=period)


_DECLARED = re.compile(r"\buniform\s+\w+\s+(u_\w+)\s*(?:\[[^\]]*\])?\s*;")


def _declared_uniforms(source: str) -> set[str]:
    """Every uniform the file's code declares — comments removed first, so
    a comment that mentions a declaration is not one."""
    code = re.sub(r"/\*.*?\*/", " ", source, flags=re.DOTALL)
    code = re.sub(r"//[^\n]*", "", code)
    return set(_DECLARED.findall(code))


def _check_clocks(name: str, spec: EffectSpec) -> None:
    """Every `@clock`'s rate is one of the file's own @param, or a product
    of them (`drift*scale`, each once) — each word as written is a key
    first, then a param's uniform (a key may itself start with `u_`) — its
    uniform is no param's, no other clock's and not
    declared by the file (this module declares it, beside u_phase)."""
    keys = {p.key for p in spec.params}
    by_uniform = {p.uniform: p.key for p in spec.params}
    declared = _declared_uniforms(spec.source)
    seen: set[str] = set()
    for k, c in enumerate(spec.clocks):
        factors: list[str] = []
        for word in c.rate.split("*"):
            if not word:
                raise SpecError(f"{name}: @clock {c.uniform} — an empty factor in its rate "
                                f"{c.rate!r} (a product is <param>*<param>, a param each side "
                                "of every `*`)")
            key = word if word in keys else by_uniform.get(word)
            if key is None:
                raise SpecError(f"{name}: @clock {c.uniform} — its rate {word!r} is no @param of "
                                "this file (a clock runs at speed × the file's own params)")
            if key in factors:
                raise SpecError(f"{name}: @clock {c.uniform} — {key!r} twice in its rate")
            factors.append(key)
        factors.sort()                  # one clock, one spelling: `scale*drift` is `drift*scale`
        if c.uniform in by_uniform or c.uniform in seen:
            raise SpecError(f"{name}: @clock {c.uniform} — that uniform is taken")
        if c.uniform in declared:
            raise SpecError(f"{name}: @clock {c.uniform} — leave the uniform undeclared: fx.py "
                            "declares every clock beside u_phase")
        seen.add(c.uniform)
        spec.clocks[k] = replace(c, rate="*".join(factors), factors=tuple(factors))


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
                    spec.order = max(0, min(int(val), 99))     # an old stack's 0…99
                elif key == "speed":
                    spec.speed = float(val)
                elif key == "mix":
                    spec.mix = max(0.0, min(float(val), 1.0))
                elif key == "blend":
                    spec.blend = BLENDS.index(val.lower())
                elif key == "clock":
                    spec.clocks.append(_parse_clock(name, n, val))
            except SpecError:
                raise                       # already says what is wrong
            except ValueError as e:
                raise SpecError(f"{name}:{n}: bad @{key} {val!r}") from e
            continue
        m = _UNIFORM.match(line)
        if not m:
            if "@param" in line:
                raise SpecError(f"{name}:{n}: @param needs 'uniform float|int u_name;' before it")
            continue
        typ, uniform, body = m.groups()
        key = uniform[2:]
        cm = _CHOICE.match(body)
        if cm or body.startswith("choice"):
            if not cm:
                raise SpecError(f'{name}:{n}: @param choice wants [a|b|…] default "Label" tip')
            if typ != "int":
                raise SpecError(f"{name}:{n}: u_{key} is a choice, so its uniform is an int")
            names = tuple(c.strip() for c in cm["names"].split("|"))
            if len(names) < 2 or not all(names) or len(set(names)) < len(names):
                raise SpecError(f"{name}:{n}: u_{key} needs two or more distinct choices")
            _check_key(name, n, key, seen)
            seen.add(key)
            spec.params.append(ParamSpec(
                key=key, uniform=uniform, label=cm["label"], lo=0.0, hi=float(len(names) - 1),
                default=float(min(int(cm["default"]), len(names) - 1)), integer=True,
                tip=cm["tip"].strip(), choices=names,
            ))
            continue
        pm = _PARAM.match(body + " ")
        if not pm:
            raise SpecError(f'{name}:{n}: @param wants lo hi default [log] [wrap] "Label" tip')
        lo, hi, default = (float(x) for x in pm["nums"].split())
        flags = pm["flags"].split()
        _check_key(name, n, key, seen)
        if not lo < hi:
            raise SpecError(f"{name}:{n}: u_{key} needs lo < hi")
        if "log" in flags and lo <= 0:
            raise SpecError(f"{name}:{n}: u_{key} is log, so lo must be > 0")
        if "amount" in flags and (lo != 0 or typ != "float" or "log" in flags
                                  or "wrap" in flags):
            raise SpecError(f"{name}:{n}: u_{key} is an amount, so it is a float from lo 0, "
                            "neither log nor wrap")
        seen.add(key)
        spec.params.append(ParamSpec(
            key=key, uniform=uniform, label=pm["label"], lo=lo, hi=hi,
            default=min(max(default, lo), hi), integer=typ == "int", log="log" in flags,
            wrap="wrap" in flags, tip=pm["tip"].strip(), amount="amount" in flags,
        ))
    if not re.search(r"\bvec4\s+effect\s*\(", source):
        raise SpecError(f"{name}: no 'vec4 effect(vec2 uv)'")
    _check_clocks(name, spec)
    return spec


class FxState:
    """The fx.* params' object: the specs on disk, their values, their clocks.

    `values[name]` holds one effect's settings by key — its four own
    (on, mix, speed, blend) and one per annotated uniform. The dicts
    are kept across a reload of the file, so a value survives an edit that
    does not remove its uniform.

    Plan 26 A4, instances: a preset's graph may hold an effect file more
    than once (`set_instances`). Instance n ≥ 2 of file `acid` is the
    effect named `acid.2` — in `specs` (the file's spec, labelled "Acid
    2"), `values`, `phase` and `names()` like any effect, so its params are
    `fx.acid.2.*` by the naming rule (`declare`), it has its own clock,
    and it runs on the file's one program. Instance 1 is the file itself,
    `acid`; where any instance runs is the graph's wires (plan 33).

    Plan 36 T3 (W3): `files` is every effect file on disk (the library the
    GRAPH picker and the migration read); `specs` is the instances that
    exist. Until a preset's graph lands that is every file once and the
    extra instances `set_instances` counts (a rig's, a tool's); once one
    does (`hold`), exactly the instances its section names — instance 1
    of a file included — and nothing else has params.
    """

    def __init__(self, directory: Path | str = FX_DIR):
        self.dir = Path(directory)
        self.on = True           # fx.on — the chain's bypass
        self.mix = 1.0           # fx.mix — scales every effect's mix
        self.face_map = PER_FACE # fx.face_map — how the faces show a picture wired into them
        self._t_last: float | None = None      # the frame time of the last advance_to
        self.specs: dict[str, EffectSpec] = {}
        self.files: dict[str, EffectSpec] = {}  # plan 36 T3: every file on disk, held or not
        # plan 36 T3: the instances a landed graph names (None: none landed —
        # every file, and `instances`' extras)
        self.held: frozenset[str] | None = None
        self.values: dict[str, dict[str, Any]] = {}
        self.phase: dict[str, float] = {}
        # the `@clock` phases: effect name → uniform → phase (read through
        # `_clocks`: an FxState from before a hot reload has no dict yet)
        self.clocks: dict[str, dict[str, float]] = {}
        self.errors: dict[str, str] = {}       # file → why it is not loaded
        self.lib = ""                          # _lib.glsl's text
        self.common = ""                       # shaders/_common.glsl's text
        # the registry's re-declare hook (params.py sets it): called with
        # the effect names whose params changed shape on a reload
        self.on_specs: Callable[[set[str]], None] | None = None
        self._mtimes: dict[str, float] = {}
        # plan 26 A4: file → how many instances the chain holds (a file not
        # named here: one, itself)
        self.instances: dict[str, int] = {}
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
            if not _NAME.match(name):
                # the naming rule (plan 26 A4): `acid.2` is the second acid
                # instance, so a file stem with a dot or of digits would read
                # as one — refused before parsing, and never kept as last good
                self.errors[name] = (f"{fname}: file names are lower_snake_case, no dot and "
                                     "not digits alone (acid.2 would read as the second "
                                     "acid instance)")
                continue
            try:
                found[name] = parse(name, (self.dir / fname).read_text())
            except (OSError, SpecError) as e:
                self.errors[name] = str(e)
                last = (getattr(self, "files", None) or self.specs).get(name)
                if last is not None:          # a broken edit keeps the last good spec
                    found[name] = last
        self.files = dict(found)
        found = self._wanted(found)
        for name in set(self.specs) - set(found):
            changed.add(name)
            self.values.pop(name, None)
            self.phase.pop(name, None)
            self._clocks().pop(name, None)
        for name, spec in found.items():
            old = self.specs.get(name)
            if old is None or old.signature() != spec.signature():
                changed.add(name)
                self._adopt(spec, name)
        self.specs = found
        return changed

    def _extras(self, files: dict[str, EffectSpec]) -> dict[str, EffectSpec]:
        """The extra instances' specs (plan 26 A4): for each file with n > 1
        instances that is on disk, `<file>.2` … `<file>.<n>`, the file's
        spec labelled with its number."""
        out: dict[str, EffectSpec] = {}
        for file, n in sorted((getattr(self, "instances", None) or {}).items()):
            spec = files.get(file)
            if spec is None:
                continue
            for k in range(2, n + 1):
                out[f"{file}.{k}"] = replace(spec, label=f"{spec.label} {k}")
        return out

    def _wanted(self, files: dict[str, EffectSpec]) -> dict[str, EffectSpec]:
        """The instances that exist over the files on disk `files`: the
        held ones (plan 36 T3, `hold`) whose file is there, else every file
        and its `instances` extras."""
        held = getattr(self, "held", None)
        if held is None:
            return {**files, **self._extras(files)}
        out: dict[str, EffectSpec] = {}
        for name in sorted(held):
            spec = files.get(name.partition(".")[0])
            n = instance_of_name(name)
            if spec is not None and (n is not None or name == spec.name):
                out[name] = spec if n is None else replace(spec, label=f"{spec.label} {n}")
        return out

    def set_instances(self, counts: dict[str, int]) -> set[str]:
        """Hold each effect file `counts` names that many times (plan 26 A4;
        a file not named, once) — a rig's or a tool's, with no graph landed
        (plan 36 T3: it lets go of any `hold`). Returns the effect names
        whose params appeared or went (`acid.2`, …) — the registry
        re-declares those (`declare`). A file that is not on disk keeps its
        count and gets its instances when it appears."""
        self.instances = {f: int(n) for f, n in counts.items() if int(n) > 1}
        self.held = None
        return self._settle()

    def hold(self, names) -> set[str]:
        """Plan 36 T3 (W3): exactly the effect instances `names` exist (a
        landed graph's, `graph.GraphSpec.effect_names`) — instance 1 of a
        file only when named; None, every file once as before a graph
        landed. Returns the names whose params appeared or went, as
        `set_instances`. A name whose file is not on disk gets its instance
        when the file appears."""
        self.held = None if names is None else frozenset(names)
        if names is None:
            self.instances = {}
        return self._settle()

    def _settle(self) -> set[str]:
        """`specs` made what `_wanted` says over the files on disk: the
        names that went and came."""
        want = self._wanted(getattr(self, "files", None) or {
            n: s for n, s in self.specs.items() if not instance_of_name(n)})
        changed: set[str] = set()
        for name in [n for n in self.specs if n not in want]:
            changed.add(name)
            del self.specs[name]
            self.values.pop(name, None)
            self.phase.pop(name, None)
            self._clocks().pop(name, None)
        for name, spec in want.items():
            if name not in self.specs:
                changed.add(name)
                self.specs[name] = spec
                self._adopt(spec, name)
        return changed

    def file_of(self, name: str) -> str:
        """The effect file an effect name runs (`acid.2` → `acid`)."""
        spec = self.specs.get(name)
        return spec.name if spec is not None else name.partition(".")[0]

    def _adopt(self, spec: EffectSpec, name: str | None = None) -> None:
        """Values for a new or re-shaped spec: keep what still exists.
        `name`: the effect's name when it is not the file's (an instance)."""
        name = spec.name if name is None else name
        old = self.values.get(name, {})
        v = {"on": bool(old.get("on", False)), "mix": float(old.get("mix", spec.mix)),
             "speed": float(old.get("speed", spec.speed)),
             "blend": int(old.get("blend", spec.blend))}
        for p in spec.params:
            x = old.get(p.key, p.default)
            v[p.key] = round(x) if p.integer else float(x)
        self.values[name] = v
        self.phase.setdefault(name, 0.0)
        # a `@clock` keeps its phase across an edit that keeps the clock;
        # one the edit dropped is forgotten, one it added starts at 0
        clocks = self._clocks()
        had = clocks.get(name, {})
        clocks[name] = {c.uniform: had.get(c.uniform, 0.0)
                        for c in getattr(spec, "clocks", ())}

    def _clocks(self) -> dict[str, dict[str, float]]:
        """The `@clock` phases, made on first use: an FxState built before
        a hot reload of this module has no `clocks` yet (its __init__ does
        not re-run), and the speed phases in `phase` are kept the same way."""
        clocks = getattr(self, "clocks", None)
        if clocks is None:
            clocks = self.clocks = {}
        return clocks

    def poll(self) -> set[str]:
        """Pick up edited, added and removed files; re-declare what changed."""
        if self._scan() == self._mtimes:
            return set()
        changed = self.load()
        if changed and self.on_specs is not None:
            self.on_specs(changed)
        return changed

    # ---- the effects ----

    def names(self) -> list[str]:
        """Every effect, by name (plan 33: no stack order — an effect's
        place is its wires)."""
        return sorted(self.specs)

    def live(self, name: str) -> bool:
        """Whether effect `name` draws this frame where it is wired (plan 33
        R): the effects on (`fx.on`) and above mix 0 (`fx.mix`), the effect
        on and above mix 0. Its place is its wires, and whether it compiled
        is the chain's to say (`FxChain.ready`)."""
        v = self.values.get(name)
        return (bool(self.on) and self.mix > 0.0 and v is not None
                and bool(v.get("on")) and float(v.get("mix", 0.0)) > 0.0)

    def advance(self, dt: float) -> None:
        """Every effect's clock by dt at its speed — on or not, so an effect
        switched on mid-set is already moving — and each of its `@clock`
        phases by dt × speed × its rate param, wrapped to its period when it
        has one. The rule (DECISIONS, "Effects"): a rate-like param is
        integrated here, never multiplied into a time in the shader, so a
        knob step changes the rate and never where the field is."""
        clocks = self._clocks()
        for n, v in self.values.items():
            speed = v["speed"]
            self.phase[n] = self.phase.get(n, 0.0) + dt * speed
            spec = self.specs.get(n)
            for c in (getattr(spec, "clocks", None) or ()):
                ph = clocks.setdefault(n, {})
                x = ph.get(c.uniform, 0.0) + dt * speed * clock_rate(c, v)
                if c.period:
                    x %= c.period
                ph[c.uniform] = x

    def advance_to(self, t: float) -> float:
        """Every effect's clock up to the frame time `t`: advance(dt) with
        dt the time since the last call, clamped to 0…0.25 s, 0 on the
        first. A second call with the same `t` advances nothing — every
        effect node of a frame calls it, and the first moves the clocks.
        Returns the dt applied."""
        # getattr: an FxState from before a hot reload has no _t_last
        last = getattr(self, "_t_last", None)
        dt = 0.0 if last is None else max(0.0, min(t - last, 0.25))
        self._t_last = t
        self.advance(dt)
        return dt


def declare(r, fx: FxState, names: set[str] | None = None) -> None:
    """The fx.* params on registry `r`: everything, or with `names` just
    those effects' (a file changed shape on reload). Bindings to an id that
    goes away go dormant, as for a deleted band."""
    g = "fx"
    if names is None:
        r.remove_prefix("fx.")
        r.toggle("fx.on", "Effects", *_attr(fx, "on"), group=g,
                 tip="Every effect's bypass: off, each reads its picture straight "
                     "through, wherever it is wired.")
        r.continuous("fx.mix", "FX mix", *_attr(fx, "mix"), lo=0.0, hi=1.0,
                     fmt=lambda v: f"mix {v:.2f}", group=g,
                     tip="Scales every effect's mix — one fader to fade them all in.")
        r.enum("fx.face_map", "Faces show", lambda: getattr(fx, "face_map", PER_FACE),
               lambda x: setattr(fx, "face_map", x), FACE_MAPS, group=g,
               tip="How a picture wired into the faces sits on the shape: per face, every "
                   "face carries the whole picture and it turns with the shape; screen, "
                   "the faces are windows onto one picture that stays still while the "
                   "shape moves across it.")
        names = set(fx.specs)
    for name in sorted(names):
        # this effect's own ids, `fx.<name>.<key>` (a key has no dot) —
        # never an instance's under it (plan 26 A4: `fx.acid.` also starts
        # `fx.acid.2.mix`, the second acid's)
        own = f"fx.{name}."
        for pid in [p.id for p in r if p.id.startswith(own) and "." not in p.id[len(own):]]:
            r.remove(pid)
        spec = fx.specs.get(name)
        if spec is None:
            continue
        v = fx.values[name]
        pre, lb = f"fx.{name}", spec.label
        r.toggle(f"{pre}.on", lb, *_key(v, "on"), group=g, tip=spec.tip)
        r.continuous(f"{pre}.mix", f"{lb} mix", *_key(v, "mix"), lo=0.0, hi=1.0,
                     fmt=lambda x: f"mix {x:.2f}", group=g,
                     tip="Wet/dry: 0 its input untouched, 1 the effect in full.")
        # wave 0 T1: on the signed exponential taper (lo / hi say the range
        # spans zero, so the panel's fill starts at the stop)
        r.continuous(f"{pre}.speed", f"{lb} speed", *_key(v, "speed"), taper=T_SPEED,
                     lo=-SPEED_MAX, hi=SPEED_MAX, fmt=fmt_speed, group=g,
                     tip="The rate of the effect's clock; negative runs it backwards, 0 "
                         "(the middle) freezes it. Exponential either side of the stop, "
                         "so 0.05× is as easy to land as 0.5×.")
        r.enum(f"{pre}.blend", f"{lb} blend", *_key(v, "blend"), BLENDS, group=g,
               tip="How the effect's output lands on its input: mix replaces, add and "
                   "screen light up, multiply darkens.")
        for p in spec.params:
            if p.choices:       # a discrete choice (plan 30 N8): a picker, never a slider
                r.enum(f"{pre}.{p.key}", f"{lb} {p.label.lower()}", *_key(v, p.key),
                       list(p.choices), group=g, tip=p.tip)
                continue
            if p.amount:        # wave 0 T1: 0 … hi on the zero-safe log taper
                r.continuous(f"{pre}.{p.key}", f"{lb} {p.label.lower()}", *_key(v, p.key),
                             taper=amount_taper(p.hi), lo=p.lo, hi=p.hi, fmt=fmt_amount,
                             group=g, tip=p.tip)
                continue
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


def fmt_speed(x: float) -> str:
    """A speed's readout: "stop" at 0, else signed with three decimals
    under 0.1× ("+0.050×"), two above ("+0.25×", "−8.00×")."""
    x = float(x)
    if x == 0:
        return "stop"
    return f"{x:+.3f}×" if abs(x) < 0.1 else f"{x:+.2f}×"


def fmt_amount(x: float) -> str:
    """An amount's readout over its ten octaves: "0" when off, else three
    significant figures as a plain decimal ("0.0016", "0.35", "16")."""
    x = float(x)
    if not x > 0:
        return "0"
    s = f"{x:.3g}"
    if "e" in s:
        s = f"{x:.{min(8, max(0, 2 - math.floor(math.log10(x))))}f}"
    return s


@functools.cache
def amount_taper(hi: float) -> tapers.Taper:
    """The zero-safe log taper an `amount` param of range 0 … `hi` is on
    (one per distinct hi, shared by every effect instance)."""
    return tapers.exp_amount(float(hi), AMOUNT_OCTAVES)


def param_of(pid: str, files: dict[str, EffectSpec]) -> tuple[EffectSpec, str] | None:
    """The effect file and key behind param id `pid` — ``fx.<file>.<key>``
    or an instance's ``fx.<file>.<n>.<key>`` (plan 26 A4) — over the specs
    `files` (`FxState.files`, file name → spec), or None for any other id."""
    parts = pid.split(".")
    if len(parts) < 3 or parts[0] != "fx":
        return None
    spec = files.get(parts[1])
    if spec is None:
        return None
    if len(parts) == 3:
        return spec, parts[2]
    mark = parts[2]
    if len(parts) == 4 and mark.isdecimal() and str(int(mark)) == mark and int(mark) >= 2:
        return spec, parts[3]
    return None


def retaper_of(pid: str, files: dict[str, EffectSpec]
               ) -> tuple[float, float, float, tapers.Taper] | None:
    """What wave 0 T1 changed under a route onto `pid`, or None when it
    changed nothing there: ``(lo, hi, default, taper)`` — the linear range
    the param had before (and still declares as `lo` / `hi`), its default
    (the base a preset that does not name it takes), and the taper it is
    on now — for an effect's `speed` and for each `amount` param. What
    `params.retaper_depths` and tools/retaper_routes.py measure a saved
    depth against."""
    got = param_of(pid, files)
    if got is None:
        return None
    spec, key = got
    if key == "speed":
        return -SPEED_MAX, SPEED_MAX, spec.speed, T_SPEED
    for p in spec.params:
        if p.key == key and p.amount:
            return p.lo, p.hi, p.default, amount_taper(p.hi)
    return None


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
uniform sampler2D u_aux;   // plan 32 R: the second picture (unit 1), wired by `<effect>.aux`
uniform int u_aux_on;      // 1 while one is wired; 0 and `aux(uv)` is transparent black
uniform vec2 u_aux_size;   // its size, px (0, 0 with none)
uniform int u_scaled;      // 1 when u_src is not the target's size
uniform ivec2 u_origin;    // the target rect's origin (gl_FragCoord is window-relative)
in vec2 v_uv;
out vec4 f_color;
"""
# the uniforms every effect has: a `@clock` may not take one of their names
HEAD_UNIFORMS = frozenset(re.findall(r"^uniform\s+\w+\s+(u_\w+)\s*;", FS_HEAD, re.MULTILINE))


def clock_declarations(clocks) -> str:
    """The `uniform float u_…;` lines for an effect's `@clock`s, part of
    the head (string 0), so a compile error's line numbers are the file's."""
    return "".join(f"uniform float {c.uniform};   // @clock: integrated by fx.py\n"
                   for c in clocks)


FS_TAIL = """
// the pixel under this one, 1:1 by texelFetch when the source is the
// target's size: llvmpipe does not land a 1:1 read through a LINEAR
// sampler on its texel (a half-float source comes back a step off)
vec4 here() {
    return u_scaled != 0 ? texture(u_src, v_uv)
                         : texelFetch(u_src, ivec2(gl_FragCoord.xy) - u_origin, 0);
}

void main() {
    vec4 a = here();
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

# an effect with no program: its source across, 1:1 by texelFetch as
# FS_TAIL's `here` reads it
COPY_FS = """
#version 330
uniform sampler2D u_src;
uniform int u_scaled;
uniform ivec2 u_origin;
in vec2 v_uv;
out vec4 f_color;
void main() {
    f_color = u_scaled != 0 ? texture(u_src, v_uv)
                            : texelFetch(u_src, ivec2(gl_FragCoord.xy) - u_origin, 0);
}
"""


def fragment_source(lib: str, effect: str, shared: str | None = None, clocks=()) -> str:
    """The whole fragment shader of an effect: the head (with the file's
    `@clock` uniforms declared), the shared helpers, the lib, the file,
    the tail."""
    shared = common() if shared is None else shared
    return (f"{FS_HEAD}{clock_declarations(clocks)}#line 1 1\n{shared}\n#line 1 2\n{lib}\n"
            f"#line 1 3\n{effect}\n#line 1 4\n{FS_TAIL}")


class FxChain:
    """The effects' textures and one program per effect, on one GL context.

    Plan 30 D0: every effect is a render graph node (`graph.Effect`), one
    pass each (`run_one`) between textures of this chain's `pool`. Plan 33
    T7: that is the only way an effect runs — the faces' chain (`run`, a
    second chain borrowing this one's programs) went with the stack; a
    branch onto the faces is effect nodes too. Every uniform is set before
    each pass, so one program serves every instance of a file in a frame."""

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
        self._frame = 0
        self.opaque = False     # the ground is opaque: every pass writes alpha 1 (Renderer.draw)
        self._build_copy()

    def _build_copy(self) -> None:
        self._copy = self.ctx.program(vertex_shader=QUAD_VS, fragment_shader=COPY_FS)
        self._copy_vao = self.ctx.vertex_array(self._copy, [])
        self._copy["u_src"].value = 0

    def on_reload(self) -> None:
        """Hot-swap hook: every program is rebuilt from source on next use."""
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

    def pool(self, size: tuple[int, int], n: int = 2
             ) -> list[tuple[moderngl.Texture, moderngl.Framebuffer]]:
        """The chain's half-float textures at `size`, at least `n` of them
        (plan 30 D0): the textures the frame's `graph.Effect` nodes paint
        into — two for a straight run of effects, one more for each effect held for the frame
        (`graph.Graph.pool`). Made again, all of them, when the size
        changes; grown by appending (a texture handed out this frame stays
        what it is); shrunk only by `fit_pool` and `release_targets`."""
        if size != self.size:
            self.release_targets()
            self.size = size
        while len(self._tex) < n:
            tex = self.ctx.texture(size, 4, dtype="f2")
            tex.repeat_x = tex.repeat_y = False
            self._tex.append(tex)
            self._fbo.append(self.ctx.framebuffer(color_attachments=[tex]))
        return list(zip(self._tex, self._fbo, strict=True))

    def fit_pool(self, n: int) -> None:
        """Release the pool when it holds more than `n` textures — a graph
        that needs fewer was built (`Renderer._graph_for`); the next use
        makes what that graph asks for."""
        if len(self._tex) > n:
            self.release_targets()

    def release_targets(self) -> None:
        for res in (*self._fbo, *self._tex):
            res.release()
        self._fbo, self._tex = [], []
        self.size = (0, 0)

    def release(self) -> None:
        """Everything this chain made on the GL context: its textures, its
        copy program and its effect programs."""
        self.release_targets()
        self._release_programs()
        self._copy_vao.release()
        self._copy.release()

    def _release_programs(self) -> None:
        """This chain's effect programs."""
        for _, prog, vao in self._progs.values():
            vao.release()
            prog.release()
        self._progs.clear()
        self._tried.clear()

    def _opaque(self) -> int:
        """u_opaque for a pass that says none: 1 over an opaque ground (a
        node on a see-through one — the hands' layer, the faces' picture —
        passes its own, `run_one`'s `opaque`)."""
        return int(getattr(self, "opaque", False))

    def _uniforms(self, prog: moderngl.Program, name: str, size: tuple[int, int],
                  t: float, opaque: int) -> None:
        """Every uniform of effect `name`'s pass over a source of `size`:
        one program serves every instance of a file, so all of them are set
        before each pass."""
        st = self.state
        w, h = size
        v = st.values[name]
        self._set(prog, "u_src", 0)
        self._set(prog, "u_res", (float(w), float(h)))
        self._set(prog, "u_phase", float(st.phase.get(name, 0.0)))
        self._set(prog, "u_time", float(t))
        self._set(prog, "u_mix", float(v["mix"]) * float(st.mix))
        self._set(prog, "u_blend", int(v["blend"]))
        self._set(prog, "u_opaque", opaque)
        self._set(prog, "u_aux", 1)
        self._set(prog, "u_aux_on", 0)
        self._set(prog, "u_aux_size", (0.0, 0.0))
        spec = st.specs[name]
        for p in spec.params:
            x = v[p.key]
            self._set(prog, p.uniform, round(x) if p.integer else float(x))
        clocks = getattr(st, "clocks", None) or {}
        for c in getattr(spec, "clocks", None) or ():
            self._set(prog, c.uniform, float(clocks.get(name, {}).get(c.uniform, 0.0)))

    def ready(self, name: str) -> bool:
        """Whether effect `name` has a program to run (built now if it has
        not been tried): False for a file that never compiled."""
        return self._program(name) is not None

    def run_one(self, name: str, src: moderngl.Texture, dst: moderngl.Framebuffer,
                t: float, opaque: int | None = None,
                aux: moderngl.Texture | None = None) -> None:
        """One effect's pass (plan 30 D0: a `graph.Effect` node's): its
        program over `src` into `dst`'s viewport, every uniform set, the
        clocks moved first (once per frame time,
        `FxState.advance_to`). An effect with no program copies `src`
        across, so `dst` always holds the picture (the node reads such an
        effect through and never asks). `opaque` (plan 30 D1): `u_opaque`
        for this pass when not the chain's — 0 for an effect placed on a
        hands' layer, whose ground is see-through whatever the window's.
        `aux` (plan 32 R): the picture wired into the effect's `aux` port,
        bound on unit 1 (`u_aux_on` 1); None leaves it off, and `aux(uv)`
        reads transparent black."""
        self.state.advance_to(t)
        pv = self._program(name)
        ctx = self.ctx
        ctx.disable(moderngl.BLEND)
        try:
            dst.use()
            src.use(location=0)
            vp = tuple(dst.viewport)
            one = {"u_scaled": int(tuple(vp[2:]) != tuple(src.size)),
                   "u_origin": (int(vp[0]), int(vp[1]))}
            if pv is None:
                for k, x in one.items():
                    self._set(self._copy, k, x)
                self._copy_vao.render(moderngl.TRIANGLES, vertices=3)
                return
            prog, vao = pv
            self._uniforms(prog, name, src.size, t,
                           self._opaque() if opaque is None else int(opaque))
            for k, x in one.items():
                self._set(prog, k, x)
            if aux is not None:
                aux.use(location=1)
                self._set(prog, "u_aux_on", 1)
                self._set(prog, "u_aux_size", tuple(float(x) for x in aux.size))
            vao.render(moderngl.TRIANGLES, vertices=3)
        finally:
            ctx.enable(moderngl.BLEND)

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
        src = fragment_source(st.lib, spec.source, st.common, getattr(spec, "clocks", ()))
        key = spec.name                 # the file: every instance of it runs one program (A4)
        have = self._progs.get(key)
        if (have is None or have[0] != src) and self._tried.get(key) != src:
            self._tried[key] = src
            try:
                prog = self.ctx.program(vertex_shader=QUAD_VS, fragment_shader=src)
            except Exception as e:  # noqa: BLE001 — a bad edit must not kill the show
                self.errors[key] = gl_error(e, {1: "_common.glsl:", 2: "_lib.glsl:", 3: "line "})
            else:
                if have is not None:
                    have[2].release()
                    have[1].release()
                self._progs[key] = have = (src, prog, self.ctx.vertex_array(prog, []))
                self.errors.pop(key, None)
        return None if have is None else (have[1], have[2])

    def compile_all(self) -> dict[str, str]:
        """Build every effect now (tests, tools); returns name → error."""
        for n in self.state.specs:
            self._program(n)
        return dict(self.errors)

    def error(self, name: str) -> str:
        """Why an effect is not what its file says: parse, then compile
        (an instance's are its file's)."""
        file = self.state.file_of(name) if hasattr(self.state, "file_of") else name
        return self.state.errors.get(file) or self.errors.get(file, "")
