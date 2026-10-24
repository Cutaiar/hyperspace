#!/usr/bin/env python3
"""Plan 26 A0 — golden frames: every factory preset in every output state
it reaches, rendered offscreen, hashed byte for byte.

Each factory preset (`preset.FACTORY_PRESETS`, the files in
`hyperspace/library/presets/`) is loaded through the real `Presets` over
a `Router` into a throwaway library home, with two synthetic hands
(`tests/fake_hands.py`: the left open, the right a fist, test_ghost's
pose) present or absent through the real `HandsIO`, and drawn through
`Renderer.draw_outputs` on eight outputs at once — the eight `Switches`
states `tests/test_outputs.py` enumerates (scene × hands × through) —
for `FRAMES` frames at `DT`, the clock pinned (`t_now = T0 + k·DT`).
Output 1 is multisampled like the window; the others are plain targets.
The LFOs and the analyzer are at rest (never stepped, never fed), the
dream is off (no worker attached), the preset's own look-back is kept,
the ghost hands are on (`ghost.on`, a session param no preset sets) and
the render cap is the app's default (1080p). Then the window's own frame,
output 1 alone (`SOLO`: the default state, and with an effect on also
through), so the pipeline is drawn direct into the multisampled target.
Once more, for one preset, a 2× HiDPI 1080p screen (3840×2160) under
that cap. And (plan 26 A3) the render graph's other wirings, hands
present (`WIRED`): the hands inside the scene (the scene's output with
the hands in it, beside a glass output that shows the hands' layer
alone, over and through) and the hands' layer laid on depth-aware, for
every preset; the history holding the hands' layer, for the presets
with the look-back on — each a rig of its own (`Renderer.wiring`), its
outputs named `<wiring>/<state>`. And (plan 26 A4b) a recorded point
cloud (`CLOUDED`): a scratch `config.toml` in the rig's home listing one
`cloud` device over the fixture recording (`tests/fixtures/clouds/`,
copied in), opened by the real device registry, polled on the pinned
clock and handed to the renderer, so the default scene gains its
point-cloud node — named `cloud/<state>`. And (plan 26 A4) the proof presets,
fixtures under `tests/fixtures/presets/` (`FIXTURE_PRESETS`, never a
factory preset): each copied into the scratch library and loaded like a
user's preset, its `graph` section landing through the real `Presets`
onto the rig's renderer, hands present, in the eight states — the
manifest's `fixture_states` and `fixtures`. And (plan 31 P) the
envelopes and the step sequencer are stepped through the router as the
app steps them — at rest and stopped, so they move nothing — but for the
presets in `RUNNING` (``seq-demo``), drawn with play pressed as the rig
starts, so their frame is the pattern mid-envelope at the pinned clock.
Plan 32's five fixtures are media
presets (`MEDIA_FIXTURES`): their bins name `local:` ids the rig's media
channels find under `tests/golden/media/` (`GoldenMedia`), every still
decoded before the first frame is drawn.

A golden is the SHA-256 of the full-resolution RGBA frame as GL returns
it, plus a quarter-size PNG for a person (one file per distinct
picture). The pipeline each state reached (`outputs.route`: SCENE,
SCENE_HANDS, HANDS or none, and the hands laid over after) is recorded
beside it, so the manifest lists what each preset actually reaches.
`tests/test_golden_frames.py` compares every hash exactly, on the
renderer the goldens were recorded on (`GL_RENDERER`), and skips with a
note elsewhere.

    uv run python tools/golden_frames.py              # diff against the goldens
    uv run python tools/golden_frames.py --record     # (re)record them
    uv run python tools/golden_frames.py --only party-trip,legacy6 [--record]

A diff writes a contact sheet of every frame that moved (golden | now |
difference ×4) under docs/plans/assets/26-render-graph/. `--record` with
`--only` re-records only those presets and keeps the rest. Nothing reads
or writes ~/Hyperspace: the library home is a temporary folder and
HYPERSPACE_HOME is pointed at another before anything is imported.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT, ROOT / "tests"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

GOLDEN = ROOT / "tests" / "golden" / "frames"
MANIFEST = GOLDEN / "frames.json"
SHEETS = ROOT / "docs" / "plans" / "assets" / "26-render-graph"

W, H = 960, 600          # the outputs' size, dpr 1
DPR = 1.0
FRAMES = 8               # frames drawn before the hash, so the echoes exist
DT = 1 / 60
T0 = 2.0                 # the pinned clock's first frame is T0 + DT
SAMPLES = 4              # output 1, like the window (app.py: glfw SAMPLES 4)
RENDER_CAP = (1920, 1080)    # overlay.RENDER_DEFAULT, "1080p"
THUMB = 4                # the PNG is 1/THUMB of the frame on each side

# the eight output states, in tests/test_outputs.py's EIGHT order
STATES: tuple[tuple[str, dict], ...] = tuple(
    ("+".join([w for w, on in (("scene", a), ("hands", b), ("through", c)) if on]) or "none",
     {"scene": a, "hands": b, "through": c})
    for a in (True, False) for b in (True, False) for c in (False, True))
HANDS = ("absent", "present")
# single-output goldens (output 1 alone, 4× MSAA, like the window): every
# preset × hands in the default state (`Switches()` = scene + hands, no
# through), and for a preset with an effect on also through. Alone, a
# pipeline has one consumer and is drawn direct into output 1 — the path
# the eight-output frame never takes — and the hands' readout split
# (`_frame_passes`: `through` over all views) is this output's alone
SOLO = (("solo", {"scene": True, "hands": True, "through": False}),)
SOLO_FX = (("solo-scene+hands+through", {"scene": True, "hands": True, "through": True}),)

# plan 26 A3: the graph's other wirings (`graph.Wiring`), hands present —
# (name, the wiring's fields, the output states drawn as one rig's
# outputs, output 1 first, the presets it is drawn for: None, every
# one). In the scene: the scene's output with the hands in it, and a glass
# (scene off) with the hands' layer over and through; depth-aware: the
# layer over at the output and through the effects; the history of the
# scene with the hands' layer — only where the look-back is on
# (`dream.on` in the file: elsewhere the history holds nothing to see)
LOOKBACK_ON = ("party-wake", "party-tracer")
WIRED: tuple[tuple[str, dict, tuple[str, ...], tuple[str, ...] | None], ...] = (
    ("in-scene", {"hands": "scene"}, ("scene+hands", "hands", "hands+through"), None),
    ("depth", {"blend": "depth"}, ("scene+hands", "scene+hands+through"), None),
    ("history+hands", {"history": "scene+hands"}, ("scene+hands",), LOOKBACK_ON),
)

# plan 26 A4b: a recorded point cloud in the scene — (name, the scratch
# config's device list, the output states, the presets), hands present.
# The device plays the fixture at its 12 fps against the pinned clock, so
# the frame drawn is the same on every run (frame 1 after FRAMES frames)
CLOUD_FIXTURE = ROOT / "tests" / "fixtures" / "clouds" / "knot.npz"
CLOUD_CONFIG = """[[devices]]
role = "scan"
kind = "cloud"
file = "clouds/knot.npz"
"""
CLOUDED: tuple[tuple[str, str, tuple[str, ...], tuple[str, ...]], ...] = (
    ("cloud", CLOUD_CONFIG, ("scene", "scene+hands"), ("legacy6", "party-faces")),
)
# plan 26 A4: the proof presets — fixtures, never factory presets (no
# file under hyperspace/library/ is edited or added) — each loaded
# through the scratch library like a user's preset, its `graph` section
# landing through the real `Presets` (`GraphSection`) onto the rig's
# renderer, hands present, every output state as one rig's outputs
FIXTURES = ROOT / "tests" / "fixtures" / "presets"
# plan 30 D1: the three placements' proof presets — the palette after the
# hands' layer, the palette into output 2's picture, a second acid after
# the scene (`graph.EffectAt.after` / `into`)
# plan 28 N4: the wire list's proof presets — hands 2 wired to output 2's
# hands alone, the palette wired into output 1's picture and a second acid
# from the history into output 2's (`graph.Wire`)
# plan 32 T6: the media channels' proof presets — a still on channel a as
# the backdrop under the scene, and channel c wired into output 2's picture
# (`graph.MediaNode`); their stills are under tests/golden/media/. Plan 32
# T7's three: the still on the faces (`view.media`), and the still wired into
# an effect's aux — blend's luma key, displace by its brightness. Plan 33
# T4's three (`hyperspace.preset/5`): the still through its own shaders onto
# the faces (`media.a → acid.2 → huecycle.2 → shape.faces`), under the scene
# (`media.a → kaleido.2 → backdrop.image`), and one branch read at two sizes
# (acid.2 on the faces at 1024² and as output 2's picture). Plan 33 T5's
# one: a switch onto the faces at select 2, the still (in1 an empty channel,
# in3 the still through acid.2: never made)
MEDIA_FIXTURES: tuple[str, ...] = ("backdrop-still", "media-to-output-2", "faces-media",
                                   "blend-luma-key", "displace-luma", "media-chain-faces",
                                   "media-chain-backdrop", "branch-two-sizes", "switch-faces")
FIXTURE_PRESETS: tuple[str, ...] = ("hands-lines", "palette-hands", "palette-glass",
                                    "acid-scene", "hands-glass-only", "wired-outputs",
                                    *MEDIA_FIXTURES)
MEDIA = ROOT / "tests" / "golden" / "media"
MEDIA_WAIT_S = 10.0      # the most a rig waits for its stills to decode (the pool)

# the one frame at the 1080p cap: a 2× HiDPI 1080p screen (3840×2160
# pixels, 1920×1080 logical) whose frame the cap keeps at 1920×1080
# plan 31 P: the presets drawn with the sequencer running (`seq.run` is
# never in a preset): play pressed as the rig starts, so step 1 fires on
# the first frame at T0 + DT and the hashed frame, FRAMES − 1 frames
# later (about 117 ms at 120 BPM), is mid-envelope on its kick (the hat
# that fired with it is over, the snare still to come: tests/
# test_plan31_wiring.py's seq-demo test steps the same frames)
RUNNING: tuple[str, ...] = ("seq-demo",)

CAP = {"preset": "party-trip", "hands": "present", "state": "scene+hands",
       "size": (3840, 2160), "logical": (1920, 1080), "dpr": 2.0}


def _scratch_home() -> None:
    """Point HYPERSPACE_HOME at a temporary folder unless a caller (the
    tests' conftest) already chose one that is not the owner's real home."""
    real = Path.home() / "Hyperspace"
    cur = os.environ.get("HYPERSPACE_HOME")
    if cur and Path(cur).resolve() != real.resolve():
        return
    os.environ["HYPERSPACE_HOME"] = tempfile.mkdtemp(prefix="hyperspace-golden-")


_scratch_home()

import fake_hands
import moderngl
import numpy as np

from hyperspace import config as config_mod
from hyperspace import devices as devices_mod
from hyperspace import envelope, lfo, sequencer, tempo
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer, legacy_layout
from hyperspace.bands import default_params
from hyperspace.control import Control
from hyperspace.fx import FxState
from hyperspace.ghost import GhostState
from hyperspace.graph import Wiring
from hyperspace.hands import HandSettings, HandsIO
from hyperspace.hands.core import features, skeleton
from hyperspace.library import Library
from hyperspace.lookback import DreamState
from hyperspace.media import ids as media_ids
from hyperspace.media.channels import MediaState
from hyperspace.media.source import FETCHING
from hyperspace.outputs import NAMES, Switches, View, route
from hyperspace.params import build_registry
from hyperspace.preset import FACTORY_PRESETS, Presets
from hyperspace.render import Renderer
from hyperspace.routing import Bindings, Router
from hyperspace.view import ViewState


def renderer_name(ctx: moderngl.Context) -> str:
    return str(ctx.info.get("GL_RENDERER", "?"))


def gl_version(ctx: moderngl.Context) -> str:
    """The driver's GL_VERSION, kept beside the renderer so a driver
    update on the same GPU is plain when a golden moves."""
    return str(ctx.info.get("GL_VERSION", "?"))


class FakeHands:
    """`LeapSource.snapshot()` over two fixed synthetic hands — or none.
    A fresh frame every poll, so the chain runs as on a live tracker."""

    status, on = "tracking", True

    def __init__(self, clock, present: bool):
        self.clock, self.seq = clock, 0
        hs = ([fake_hands.hand("left", "open", (-90.0, 210.0, 0.0)),
               fake_hands.hand("right", "fist", (90.0, 200.0, 10.0))] if present else [])
        self.hands = {h.type.name.lower(): (features(h), float(h.confidence)) for h in hs}
        self.skel = {h.type.name.lower(): skeleton(h) for h in hs}

    def snapshot(self):
        self.seq += 1
        return self.seq, self.clock(), self.hands, self.skel

    def latest(self):
        seq, t, hands, _ = self.snapshot()
        return seq, t, hands

    def close(self) -> None:
        pass


class GoldenMedia:
    """The rig's media resolver (plan 32 T6): a `local:` id is a file under
    `tests/golden/media/`; nothing else is on this Mac."""

    proxy_cache = None

    def path(self, sid: str):
        got = media_ids.parse(sid)
        if got.kind != "local":
            return None
        p = MEDIA / got.ref
        return p if p.is_file() else None

    def live(self, sid: str):
        return None


class NullOut:
    name = "none"

    def send(self, m) -> None:
        pass


@dataclass
class Shot:
    """One golden: what was drawn and the frame's hash."""

    preset: str
    hands: str
    state: str
    route: str           # the pipeline the state reached: SCENE, SCENE_HANDS, HANDS, none
    over: bool           # the hands laid over after the pipeline
    sha256: str
    size: tuple[int, int]
    pixels: np.ndarray   # (h, w, 4) uint8, top row first: for the PNG and a diff
    wired: str | None = None   # plan 28 N4: what feeds a wired output's picture

    @property
    def key(self) -> str:
        return f"{self.preset}|{self.hands}|{self.state}"

    def entry(self) -> dict:
        out = {"preset": self.preset, "hands": self.hands, "state": self.state,
               "route": self.route, "hands_over": self.over, "size": list(self.size),
               "sha256": self.sha256, "png": f"png/{self.sha256[:16]}.png"}
        if self.wired is not None:          # (only a wired output's entry has it)
            out["wired"] = self.wired
        return out


class Rig:
    """One preset, hands present or absent, on the tool's one context
    (`context()`), with a renderer of its own: the registry, the router,
    the hands chain, the renderer."""

    def __init__(self, slug: str, hands: str, ctx: moderngl.Context):
        """A factory preset by its slug, or a fixture (`FIXTURE_PRESETS`):
        copied into the scratch library first and loaded from there."""
        self.t = T0
        self.view, self.fx, self.dream, self.ghost = (ViewState(), FxState(), DreamState(),
                                                      GhostState())
        chain = Analyzer(Analyser(48_000), default_params(), layout=legacy_layout())
        # plan 32: the channels the `media.*` params write and the preset's
        # bins fill, as app.main makes them (here over the golden stills)
        self.media = MediaState(GoldenMedia())
        self.reg = reg = build_registry(self.view, Control(chain), SimpleNamespace(chain=chain),
                                        None, self.dream, self.fx, ghost=self.ghost,
                                        media=self.media)
        self.clock = tempo.Clock(now=lambda: self.t)
        tempo.register(reg, self.clock)
        lfo.register(reg, lfo.LFOs(), self.clock)      # declared, never stepped: at rest
        # plan 31 P: the envelopes and the sequencer, stepped as the app
        # steps them — at rest and stopped unless the preset is in
        # `RUNNING`, so no other golden sees them
        self.envs, self.seq = envelope.Envelopes(), sequencer.Sequencer()
        envelope.register(reg, self.envs, self.clock)
        sequencer.register(reg, self.seq, self.clock)
        self._home = tempfile.TemporaryDirectory(prefix="hyperspace-golden-lib-")
        if slug in FIXTURE_PRESETS:          # a user's preset in the scratch library
            own = Path(self._home.name) / "presets"
            own.mkdir(parents=True, exist_ok=True)
            (own / f"{slug}.json").write_text((FIXTURES / f"{slug}.json").read_text())
        lib = Library(Path(self._home.name))
        lib.attach(reg)
        self.router = Router(reg, Bindings())
        self.router.use_bank(self.envs, self.clock)
        self.router.use_sequencer(self.seq, self.envs, self.clock)
        presets = self.presets = Presets(lib, reg, self.router)
        self.missing = presets.load(slug)
        self.notes = list(presets.notes)
        reg["ghost.on"].set(True)
        # plan 28 N4: a second hands node the graph declares shows too (its
        # own `ghost.<n>.on`, the session's like `ghost.on`); only a fixture
        # declares one, so no other golden sees this
        for pid in [p.id for p in reg if re.fullmatch(r"ghost\.[0-9]+\.on", p.id)]:
            reg[pid].set(True)
        self.io = HandsIO(HandSettings.from_config({}), {"enabled": True},
                          source=FakeHands(lambda: self.t, hands == "present"),
                          out=NullOut(), clock=lambda: self.t)
        self.clock.trigger(self.t)
        if slug in RUNNING:
            # the transport is the session's (decision 8): pressed play,
            # the pattern restarting at step 1 on the first frame (T0 + DT)
            self.seq.run = True
            self.seq.restart()
        self.ctx = ctx
        r = self.renderer = Renderer(ctx, dream=self.dream, fx=self.fx, ghost=self.ghost)
        # plan 26 A4: the preset's graph (none for a factory preset: the
        # default wiring) onto this renderer, as app.py attaches it
        presets.graph.attach(r)
        r.max_frame = RENDER_CAP
        errs = r.fx.compile_all()
        if errs:
            raise RuntimeError(f"fx shaders failed to build: {errs}")
        r.ghost.source, r.ghost.router = self.io, self.router
        self.devices = None          # plan 26 A4b: a device registry, polled each frame
        # plan 32: the channels on the renderer, as app.main hands them; the
        # stills the preset's slots name opened and decoded before the first
        # frame (the pool's job: a golden must not catch one half-way)
        r.media = self.media
        self.media.poll(0.0, self.t)
        until = time.monotonic() + MEDIA_WAIT_S
        while any(ch.source is not None and ch.source.status == FETCHING
                  for ch in self.media.channels.values()):
            if time.monotonic() > until:
                raise RuntimeError(f"{slug}: a media still did not decode in {MEDIA_WAIT_S} s")
            time.sleep(0.01)

    def list_devices(self, toml: str) -> None:
        """A scratch `config.toml` in the rig's home listing `toml`'s
        devices (the cloud fixture copied in beside it), opened by the real
        registry on the pinned clock and handed to the renderer."""
        import shutil

        home = Path(self._home.name)
        (home / "clouds").mkdir(exist_ok=True)
        shutil.copy(CLOUD_FIXTURE, home / "clouds" / CLOUD_FIXTURE.name)
        (home / "config.toml").write_text(toml)
        cfg = config_mod.load(home / "config.toml")
        self.devices = devices_mod.DeviceRegistry(
            config_mod.devices(cfg), devices_mod.Context(home=home), clock=lambda: self.t)
        self.devices.open_all()
        self.renderer.cloud_source = self.devices

    def close(self) -> None:
        self.media.close()
        self._home.cleanup()

    def frame(self, views: list[View], logical: tuple[int, int], dpr: float) -> None:
        """One frame in the app's order, LFOs and analyzer left out:
        hands → modulate → apply → integrate → draw."""
        self.t += DT
        if self.devices is not None:
            self.devices.poll(DT, self.t)
        self.media.poll(DT, self.t)
        self.io.poll(DT, None, self.router)
        self.clock.tick(self.t)
        self.router.modulate()
        self.reg.apply()
        self.view.integrate(DT)
        self.renderer.draw_outputs(self.view, *logical, dpr, views, t_now=self.t)


def _target(ctx, size, samples=0):
    return ctx.framebuffer(color_attachments=[ctx.renderbuffer(size, 4, samples=samples)])


def _read(ctx, fbo, size) -> np.ndarray:
    """(h, w, 4) uint8 as GL returns it (bottom row first), a multisampled
    target resolved first."""
    if fbo.color_attachments[0].samples:
        flat = _target(ctx, size)
        ctx.copy_framebuffer(flat, fbo)
        data = flat.read(components=4)
    else:
        data = fbo.read(components=4)
    return np.frombuffer(data, dtype=np.uint8).reshape(size[1], size[0], 4)


_CTX: moderngl.Context | None = None
_PARK = None       # a 1×1 framebuffer bound between rigs, so none of theirs is


def context() -> moderngl.Context:
    """The one standalone context every rig draws on, made once and kept
    (releasing a context leaves none current, which strands the caller's;
    tests/test_golden_frames.py uses this one too). Its objects are freed
    when they are collected (`gc_mode` auto), so each rig's renderer goes
    with the rig (`render_all` collects after each)."""
    global _CTX, _PARK
    if _CTX is None:
        _CTX = moderngl.create_context(standalone=True)
        _CTX.gc_mode = "auto"
        _PARK = _target(_CTX, (1, 1))
    return _CTX


def _shoot(slug: str, hands: str, states, size, logical, dpr,
           wiring: dict | None = None, config: str | None = None) -> tuple[list[Shot], dict]:
    """Render one rig's states (under `wiring`, the default graph's when
    None; with `config`'s devices listed, A4b); its shots and what the load
    said. The framebuffers and the renderer are new per rig, so nothing a
    rig drew reaches the next."""
    ctx = context()
    rig = Rig(slug, hands, ctx)
    if wiring is not None:
        rig.renderer.wiring = Wiring(**wiring)
    if config is not None:
        rig.list_devices(config)
    try:
        targets = [_target(ctx, size, SAMPLES if k == 0 else 0) for k in range(len(states))]
        views = [View(Switches(**sw), size, target=f) for f, (_, sw) in zip(targets, states)]
        for _ in range(FRAMES):
            rig.frame(views, logical, dpr)
        assert ctx.error == "GL_NO_ERROR", ctx.error
        for v in views:
            if v.error:
                raise RuntimeError(f"{slug} {hands}: an output failed: {v.error}")
        fx_on = rig.renderer.fx.active()
        visible = bool(rig.renderer.stats.get("layer") or rig.renderer.stats.get("in_scene"))
        shots = []
        for k, ((name, sw), f) in enumerate(zip(states, targets)):
            # the pipeline the graph's output settled on (plan 26 A3: the
            # wiring); with the default wiring it is `outputs.route`'s
            key, over = rig.renderer.stats["routes"][k]
            if wiring is None and rig.renderer.wiring == Wiring():    # (a fixture's graph: its own)
                assert (key, over) == route(Switches(**sw), fx_on, visible), (slug, name)
            raw = _read(ctx, f, size)
            # plan 28 N4: an output whose picture is a wire's shows no
            # pipeline of `outputs.route`'s table (its end is its own,
            # `graph.Wired`, keyed `wire(output.<n>)`): its route reads
            # "none" and its entry says what feeds the wire (`wired`); any
            # other key not in the table is a bug, and raises here
            wired = None
            if isinstance(key, str) and key.startswith("wire("):
                port = f"{key[len('wire('):-1]}.image"
                wired = next(w.src for w in rig.renderer.wiring.wires if w.dst == port)
                route_name = "none"
            else:
                route_name = NAMES[key] if key is not None else "none"
            shots.append(Shot(slug, hands, name, route_name,
                              bool(over), hashlib.sha256(raw.tobytes()).hexdigest(),
                              tuple(size), raw[::-1].copy(), wired))
        said = {"missing": sorted(rig.missing), "notes": rig.notes,
                "effects_on": bool(fx_on), "hands_shown": visible}
        if slug in FIXTURE_PRESETS:     # what the graph landed, and the nodes timed
            said["graph"] = rig.presets.graph.doc     # the section as it landed, not a repr
            said["nodes"] = list(rig.renderer._graph.timed)
        return shots, said
    finally:
        rig.close()
        _PARK.use()        # never free a bound framebuffer (see test_outputs.today)


def render_all(only: set[str] | None = None, *, cap: bool = True) -> tuple[list[Shot], dict]:
    """Every golden (or only the presets in `only`), and per preset what
    its load said."""
    shots: list[Shot] = []
    said: dict[str, dict] = {}
    for slug in FACTORY_PRESETS:
        if only and slug not in only:
            continue
        for hands in HANDS:
            got, info = _shoot(slug, hands, STATES, (W, H), (W, H), DPR)
            gc.collect()        # the rig's GL objects, freed now (gc_mode auto)
            shots += got
            said.setdefault(slug, {})[hands] = info
            # the window's own frame: output 1 alone, so its pipeline is
            # drawn direct into the multisampled target and the hands'
            # readout is decided by this one output (see SOLO)
            solo = SOLO + (SOLO_FX if info["effects_on"] else ())
            for one in solo:
                got, _ = _shoot(slug, hands, (one,), (W, H), (W, H), DPR)
                gc.collect()
                shots += got
            if hands != "present":
                continue
            for wired, wiring, names, which in WIRED:
                if which is not None and slug not in which:
                    continue
                got, _ = _shoot(slug, hands, tuple((n, dict(STATES)[n]) for n in names),
                                (W, H), (W, H), DPR, wiring)
                gc.collect()
                for sh in got:
                    sh.state = f"{wired}/{sh.state}"
                shots += got
            for name, toml, names, which in CLOUDED:
                if slug not in which:
                    continue
                got, _ = _shoot(slug, hands, tuple((n, dict(STATES)[n]) for n in names),
                                (W, H), (W, H), DPR, config=toml)
                gc.collect()
                for sh in got:
                    sh.state = f"{name}/{sh.state}"
                shots += got
    for slug in FIXTURE_PRESETS:
        if only and slug not in only:
            continue
        got, info = _shoot(slug, "present", STATES, (W, H), (W, H), DPR)
        gc.collect()
        shots += got
        said.setdefault(slug, {})["present"] = info
    if cap and (not only or CAP["preset"] in only):
        state = dict(STATES)[CAP["state"]]
        got, _ = _shoot(CAP["preset"], CAP["hands"], ((CAP["state"], state),), CAP["size"],
                        CAP["logical"], CAP["dpr"])
        gc.collect()
        for s in got:
            s.state = f"{CAP['state']}@{CAP['size'][0]}x{CAP['size'][1]}-cap1080p"
        shots += got
    return shots, said


def _thumb(pixels: np.ndarray):
    """The PNG's picture: 1/THUMB a side, box-filtered, 256 colours."""
    from PIL import Image

    h, w = pixels.shape[:2]
    im = Image.fromarray(pixels[..., :3]).resize((w // THUMB, h // THUMB), Image.BOX)
    return im.quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)


def _png(shot: Shot, path: Path) -> None:
    _thumb(shot.pixels).save(path, optimize=True)


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text())


def record(shots: list[Shot], said: dict, renderer: str, only: set[str] | None,
           version: str = "?") -> dict:
    """Write the manifest (merged with the presets not re-recorded under
    `only`) and a PNG per distinct picture; drop PNGs nothing names."""
    GOLDEN.mkdir(parents=True, exist_ok=True)
    (GOLDEN / "png").mkdir(exist_ok=True)
    old = load_manifest() if (only and MANIFEST.exists()) else {"goldens": [], "presets": {}}
    if only and old.get("renderer") != renderer:
        raise SystemExit(f"--only re-records into goldens made on {old.get('renderer')!r}; "
                         f"this is {renderer!r}: record them all")
    redone = {s.preset for s in shots}
    entries = [e for e in old["goldens"] if e["preset"] not in redone] + [s.entry() for s in shots]
    order = {slug: k for k, slug in enumerate((*FACTORY_PRESETS, *FIXTURE_PRESETS))}
    st = {name: k for k, (name, _) in enumerate(STATES)}
    entries.sort(key=lambda e: (order[e["preset"]], HANDS.index(e["hands"]),
                                st.get(e["state"], len(st)), e["state"]))
    presets = {k: v for k, v in old.get("presets", {}).items() if k not in redone}
    presets.update({k: v for k, v in said.items() if k not in FIXTURE_PRESETS})
    fixtures = {k: v for k, v in old.get("fixtures", {}).items() if k not in redone}
    fixtures.update({k: v for k, v in said.items() if k in FIXTURE_PRESETS})
    doc = {
        "about": "plan 26 A0 golden frames: tools/golden_frames.py --record writes this; "
                 "tests/test_golden_frames.py compares every sha256 exactly. Far fewer "
                 "pictures than goldens are distinct, by design: with hands absent the "
                 "hands switch and through change nothing, with no effect on through is "
                 "hands over, and every state with no scene and no hand shown is the "
                 "same black ground",
        "renderer": renderer,
        "gl_version": version,
        "size": [W, H], "dpr": DPR, "frames": FRAMES, "dt": DT, "t0": T0,
        "samples_output_1": SAMPLES, "render_cap": list(RENDER_CAP),
        "hands_present": "tests/fake_hands.py: left open at (-90, 210, 0), right fist at "
                         "(90, 200, 10) mm; ghost.on true",
        "states": {name: sw for name, sw in STATES},
        "solo_states": {name: sw for name, sw in SOLO + SOLO_FX},
        "solo_fx_only": [name for name, _ in SOLO_FX],
        "wired_states": {name: {"wiring": wiring, "states": list(names),
                                "presets": None if which is None else list(which)}
                         for name, wiring, names, which in WIRED},
        "cloud_states": {name: {"config": toml, "fixture": "tests/fixtures/clouds/knot.npz",
                                "states": list(names), "presets": list(which)}
                         for name, toml, names, which in CLOUDED},
        "cap": {**CAP, "size": list(CAP["size"]), "logical": list(CAP["logical"])},
        "sequencer_running": list(RUNNING),
        "fixture_states": {slug: {"file": f"tests/fixtures/presets/{slug}.json",
                                  "hands": "present", "states": [n for n, _ in STATES]}
                           for slug in FIXTURE_PRESETS},
        "presets": {k: presets[k] for k in sorted(presets, key=order.__getitem__)},
        "fixtures": {k: fixtures[k] for k in sorted(fixtures, key=order.__getitem__)},
        "goldens": entries,
    }
    MANIFEST.write_text(json.dumps(doc, indent=1) + "\n")
    for s in shots:
        p = GOLDEN / s.entry()["png"]
        if not p.exists():
            _png(s, p)
    named = {e["png"].split("/", 1)[1] for e in entries}
    for p in (GOLDEN / "png").glob("*.png"):
        if p.name not in named:
            p.unlink()
    return doc


def diff(shots: list[Shot], doc: dict) -> list[tuple[Shot, dict | None]]:
    """The shots whose hash is not the golden's (or that have no golden)."""
    want = {f"{e['preset']}|{e['hands']}|{e['state']}": e for e in doc["goldens"]}
    return [(s, want.get(s.key)) for s in shots
            if want.get(s.key) is None or want[s.key]["sha256"] != s.sha256]


def contact_sheet(moved: list[tuple[Shot, dict | None]], path: Path) -> Path:
    """golden | now | |difference| × 4, one row per moved frame, labelled.
    Both sides are the PNG's thumbnail (`_thumb`), so the difference is
    the frames' and not the thumbnail's; the exact test is the hash."""
    from PIL import Image, ImageDraw

    tw, th = W // 2, H // 2
    rows = max(len(moved), 1)
    sheet = Image.new("RGB", (3 * tw, rows * (th + 18)), "black")
    d = ImageDraw.Draw(sheet)
    for k, (s, e) in enumerate(moved):
        y = k * (th + 18)
        now = _thumb(s.pixels).convert("RGB").resize((tw, th), Image.NEAREST)
        gp = GOLDEN / e["png"] if e is not None else None
        if gp is not None and gp.exists():
            old = Image.open(gp).convert("RGB").resize((tw, th), Image.NEAREST)
        else:
            old = Image.new("RGB", (tw, th), "black")
        delta = np.clip(np.abs(np.asarray(now, int) - np.asarray(old, int)) * 4, 0, 255)
        for c, im in enumerate((old, now, Image.fromarray(delta.astype(np.uint8)))):
            sheet.paste(im, (c * tw, y + 18))
        d.text((4, y + 3), f"{s.preset} · hands {s.hands} · {s.state} ({s.route})"
               + ("" if e else " — no golden"), fill="white")
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)
    return path


def summary(doc: dict) -> str:
    """Per preset: each state's pipeline, hands absent / present."""
    by: dict[tuple[str, str], dict[str, str]] = {}
    for e in doc["goldens"]:
        by.setdefault((e["preset"], e["hands"]), {})[e["state"]] = (
            e["route"] + ("+over" if e["hands_over"] else ""))
    lines = [(f"renderer: {doc['renderer']} ({doc.get('gl_version', '?')}); "
              f"{len(doc['goldens'])} goldens, "
              f"{len({e['sha256'] for e in doc['goldens']})} distinct pictures "
              "(hands absent, no effect on and no scene collapse states onto one picture)")]
    for (slug, hands), states in by.items():
        lines.append(f"  {slug:<14} hands {hands:<7} " + "  ".join(
            f"{k}={v}" for k, v in states.items()))
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--record", action="store_true", help="write the goldens")
    ap.add_argument("--only", default="", help="comma-separated preset slugs")
    a = ap.parse_args()
    only = {x.strip() for x in a.only.split(",") if x.strip()} or None
    if only and (unknown := only - set(FACTORY_PRESETS) - set(FIXTURE_PRESETS)):
        ap.error(f"no such preset: {', '.join(sorted(unknown))}")
    renderer, version = renderer_name(context()), gl_version(context())
    shots, said = render_all(only)
    if a.record:
        doc = record(shots, said, renderer, only, version)
        print(f"recorded {len(shots)} goldens under {GOLDEN.relative_to(ROOT)}")
        print(summary(doc))
        return
    doc = load_manifest()
    if doc["renderer"] != renderer:
        raise SystemExit(f"the goldens were recorded on {doc['renderer']!r} "
                         f"({doc.get('gl_version', '?')}); this context is {renderer!r} "
                         f"({version}): a diff here means nothing")
    moved = diff(shots, doc)
    if not moved:
        print(f"all {len(shots)} frames match their goldens ({renderer}, {version})")
        return
    if doc.get("gl_version") != version:
        print(f"note: recorded on GL_VERSION {doc.get('gl_version')!r}, this is {version!r}")
    tag = "-".join(sorted(only)) if only else "all"
    path = contact_sheet(moved, SHEETS / f"golden-diff-{tag}.png")
    for s, e in moved:
        print(f"MOVED {s.key} ({s.route})" + ("" if e else " — no golden"))
    print(f"{len(moved)} of {len(shots)} frames moved; sheet: {path.relative_to(ROOT)}")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
