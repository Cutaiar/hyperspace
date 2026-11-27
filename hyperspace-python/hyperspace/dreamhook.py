"""The dream effect's Python half (plan 90 H3: `shaders/fx/dream.glsl`,
`// @hook dream`) — the dream as an effect file, with nothing of its own on
show but its knobs.

What it does, in its pass (`run`, from `fx.FxChain.run_one`):

- **pull** the worker's newest result into the instance's result texture —
  one of another size (the input changed size since its submit) is skipped;
- **submit** the input when the worker is free (`ready()`, plan 90 Q8:
  one readback a job, not one a frame) and at most once a frame: the input
  copied into an RGBA8 target at its own size, read back once, handed over
  with the knobs (`params`): Hold, layer, passes, strength, jitter, scales;
- **draw** the file: the result on unit 2 (`u_dream`, `u_dream_on` 1), or
  its input until the first result lands.

The worker (`dream.DreamWorker`, torch, only when `[dream] enabled`) hangs
on the chain as `chain.dream_source` (app.py; a deck fade lends it,
`deck.Fade`). It is a `Source`: ``submit(frame, index, params)``,
``latest() → (pixels, index) | None``, and optionally ``ready()`` and
``buffer(shape)`` (the alias copy path). Without one the dream passes its
picture through, said. A numpy fake drives every test (torch is not
installed in the cloud).

**One live dream** (D2: one worker, one GPU job): the first instance to run
holds the worker; another that runs while it does passes its picture
through, said, until the holder stops running for a frame.

The layer list (`LAYERS`, in the file's stored order: append only) and the
words about each (`LAYER_INFO`) live here, so nothing that draws a menu
imports torch.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import moderngl
import numpy as np

# dream.layer's choices in their stored order (the file's `u_layer` choice): a
# save keeps the index, so a new layer is appended, never inserted
LAYERS = ["conv2_2", "conv3_3", "conv4_3", "inception3b", "inception4c", "inception4e",
          "conv1_1", "conv1_2", "conv2_1", "conv3_1", "conv3_2", "conv4_1", "conv4_2",
          "conv5_1", "conv5_2", "conv5_3",
          "conv1", "conv2", "conv3", "inception3a", "inception4a", "inception4b",
          "inception4d", "inception5a", "inception5b"]
OCTAVES = ["1", "2 alt", "3 alt"]       # one scale a job, in rotation (spike D)
# name → (net, short, long), by net, shallow → deep. From two contact sheets
# (docs/plans/assets/20-fx-dream-looks/dream-layers*.jpg, tools/dream_layer_sheet.py:
# one to two seconds of dreaming at the defaults, 256 px, the owner's laptop over
# MPS); "slower" is over 25 ms a job there, where conv3_3 takes about 19
LAYER_INFO: dict[str, tuple[str, str, str]] = {
    "conv1_1": ("VGG16", "flat colour, fine dots",
                "The first layer: colours pushed to a few flat, bold ones under a fine "
                "mesh of dots. Almost no shapes of its own."),
    "conv1_2": ("VGG16", "colour split, fine dots",
                "Colours split into a fine red-and-blue dot mesh along every edge. Still "
                "no shapes of its own."),
    "conv2_1": ("VGG16", "fine hatching",
                "Fine hatching and moiré, muted colour: the picture looks engraved."),
    "conv2_2": ("VGG16", "dense neon cells",
                "A dense mesh of small neon cells, green and magenta, that fills whatever "
                "is lit. Strong and busy."),
    "conv3_1": ("VGG16", "woven stripes", "Short stripes woven at angles, a fine textile texture."),
    "conv3_2": ("VGG16", "fine maze",
                "A fine maze of little loops and stripes; the start of the classic swirl."),
    "conv3_3": ("VGG16", "small loops, the classic",
                "Small loops, rings and swirls woven together: the classic Deep Dream "
                "texture, and the default."),
    "conv4_1": ("VGG16", "soft rings", "Soft rings and dots, spaced out over a smoother ground."),
    "conv4_2": ("VGG16", "eyelets and scales",
                "Eye-like rings and scale-like cells, larger than conv3's."),
    "conv4_3": ("VGG16", "blots and eyes, slower",
                "Bigger blots with eye-like rings where lines meet. Slower: about 27 ms a "
                "job at 256 px."),
    "conv5_1": ("VGG16", "large swirls, slower",
                "The deepest VGG layers: large soft swirls and blobs, detail gathered at "
                "the corners. Slower: about 28 ms a job."),
    "conv5_2": ("VGG16", "large swirls, slower",
                "Large soft swirls and blobs, like conv5_1, a little looser. Slower: "
                "about 30 ms a job."),
    "conv5_3": ("VGG16", "largest blobs, slower",
                "VGG's last layer: the largest blobs and swirls; by its depth, the most "
                "object-like VGG gets. Slower: about 30 ms a job."),
    "conv1": ("GoogLeNet", "coarse colour dots",
              "GoogLeNet's first layer: a coarse grid of bold coloured dots."),
    "conv2": ("GoogLeNet", "rainbow ripples", "Fine wavy lines in rainbow fringes, like moiré."),
    "conv3": ("GoogLeNet", "specks and dashes",
              "Small specks and dashes along the edges, light on the ground."),
    "inception3a": ("GoogLeNet", "ripples and scales",
                    "Ripples and scale-like waves, the first of the inception blocks."),
    "inception3b": ("GoogLeNet", "rings and pits",
                    "Small rings with dark pits in them, eyelets over everything."),
    "inception4a": ("GoogLeNet", "rings and curls", "Concentric rings and curls, larger than 3b's."),
    "inception4b": ("GoogLeNet", "curls and stars",
                    "Curls and small starbursts; the start of the creature-like forms."),
    "inception4c": ("GoogLeNet", "shells and spirals",
                    "Big shell- and fan-like spirals. Deep Dream's well-known eyes, dog faces "
                    "and pagodas come from around here (4c to 5a) given time and strength."),
    "inception4d": ("GoogLeNet", "creature textures",
                    "Patchy, fur- and skin-like textures with the odd eye; object-like parts "
                    "given time."),
    "inception4e": ("GoogLeNet", "large soft forms",
                    "Larger, softer wavy forms; less fine texture than 4c and 4d."),
    "inception5a": ("GoogLeNet", "faint relief, slower",
                    "Deep and coarse: a faint relief at the default strength, larger forms "
                    "with more. Slower: about 28 ms a job."),
    "inception5b": ("GoogLeNet", "faint relief, slower",
                    "GoogLeNet's last block: the faintest at the default strength, the "
                    "largest forms. Slower: about 29 ms a job."),
}
DREAM_UNIT = 2              # the result's texture unit (fx: 2 is a hook's)

NO_WORKER = ("no dream worker ([dream] enabled = true in config.toml, and torch): "
             "the picture passes through")
ONE_DREAM = "one live dream at a time (one worker, one GPU job): {holder} holds it — this passes through"
WAITING = "waiting for the dream worker"
DREAMING = "{w}×{h} · the dream worker's, a job or two late"


@runtime_checkable
class Source(Protocol):
    """What the dream hands its picture to (`dream.DreamWorker`, or a fake)."""

    def submit(self, frame: np.ndarray, frame_index: int,
               params: dict[str, Any] | None = None) -> None: ...

    def latest(self) -> tuple[np.ndarray, int] | None: ...


def params_of(values: dict[str, Any]) -> dict[str, Any]:
    """The worker's knobs from an instance's values (`fx.dream.*`)."""
    layer = int(values.get("layer", 1))
    octaves = int(values.get("octaves", 0))
    return {"k": float(values.get("k", 1.0)),
            "layer": LAYERS[min(max(layer, 0), len(LAYERS) - 1)],
            "steps": max(1, int(values.get("steps", 2))),
            "step": float(values.get("step", 0.03)),
            "jitter": max(0, int(values.get("jitter", 8))),
            "octaves": min(max(octaves, 0), len(OCTAVES) - 1)}


class Gl:
    """A chain's dream objects: the result texture, the readback target, and
    who holds the one worker. Made on first use (`gl_of`)."""

    def __init__(self) -> None:
        self.holder: str | None = None      # the instance that holds the worker
        self.ran: dict[str, int] = {}       # instance → the chain frame it last ran in
        self.submitted_in = -1              # the chain frame of the last submit
        self.submits = 0                    # submits made (the frame index handed over)
        self.shown = -1                     # the submit the result answers; −1 none yet
        self.size = (0, 0)
        self.result: moderngl.Texture | None = None
        self.small: moderngl.Texture | None = None
        self.fbo: moderngl.Framebuffer | None = None
        self._host: np.ndarray | None = None

    def ensure(self, ctx: moderngl.Context, size: tuple[int, int]) -> None:
        if size == self.size and self.result is not None:
            return
        self.release()
        self.result = ctx.texture(size, 4)
        self.result.repeat_x = self.result.repeat_y = False
        self.small = ctx.texture(size, 4)
        self.fbo = ctx.framebuffer(color_attachments=[self.small])
        self.size = size
        self.shown = -1

    def buffer(self, source: Any) -> np.ndarray:
        w, h = self.size
        shape = (h, w, 4)
        alloc = getattr(source, "buffer", None)
        if alloc is not None:
            got = alloc(shape)
            if got is not None:
                return got
        if self._host is None or self._host.shape != shape:
            self._host = np.empty(shape, dtype=np.uint8)
        return self._host

    def release(self) -> None:
        for res in (self.fbo, self.small, self.result):
            if res is not None:
                res.release()
        self.fbo = self.small = self.result = None
        self.size = (0, 0)
        self.shown = -1


def gl_of(chain) -> Gl:
    got = getattr(chain, "dream", None)
    if not isinstance(got, Gl):
        if got is not None:
            got.release()
        got = chain.dream = Gl()
    return got


def tick(chain) -> None:
    """Once a frame (`FxChain.tick`): the holder that did not run last frame
    lets the worker go."""
    gl = getattr(chain, "dream", None)
    if gl is None:
        return
    if not isinstance(gl, Gl):                # a hot reload: made again on next use
        gl.release()
        chain.dream = None
        return
    now = getattr(chain, "_frame", 0)
    if gl.holder is not None and gl.ran.get(gl.holder, -10) < now - 1:
        gl.holder = None
        gl.shown = -1


def release(chain) -> None:
    gl = getattr(chain, "dream", None)
    if gl is not None:
        gl.release()
        chain.dream = None


def advance(spec, values: dict, dt: float) -> None:
    """No drives: the dream's own time is the worker's."""


def _say(chain, name: str, words: str) -> None:
    said = getattr(chain, "said", None)
    if isinstance(said, dict):
        said[name] = words


def run(chain, name: str, prog: moderngl.Program, vao: moderngl.VertexArray,
        src: moderngl.Texture, dst: moderngl.Framebuffer) -> None:
    """The dream's pass (module docstring): pull, submit when free, draw."""
    gl = gl_of(chain)
    now = getattr(chain, "_frame", 0)
    gl.ran[name] = now
    source = getattr(chain, "dream_source", None)
    if gl.holder is None:
        gl.holder = name
    on = 0
    if gl.holder != name:
        _say(chain, name, ONE_DREAM.format(holder=gl.holder))
    elif source is None:
        _say(chain, name, NO_WORKER)
    else:
        ctx = chain.ctx
        vp = tuple(dst.viewport)
        gl.ensure(ctx, tuple(src.size))
        _pull(gl, source)
        ready = getattr(source, "ready", None)
        if gl.submitted_in != now and (ready is None or ready()):
            _submit(chain, gl, source, src, name)
            gl.submitted_in = now
            dst.use()
            ctx.viewport = vp
            ctx.disable(moderngl.BLEND)
            src.use(location=0)
        on = int(gl.shown >= 0)
        w, h = gl.size
        _say(chain, name, DREAMING.format(w=w, h=h) if on else WAITING)
    if on:
        gl.result.use(location=DREAM_UNIT)
    if "u_dream" in prog:
        prog["u_dream"].value = DREAM_UNIT
    if "u_dream_on" in prog:
        prog["u_dream_on"].value = on
    vao.render(moderngl.TRIANGLES, vertices=3)


def _pull(gl: Gl, source: Any) -> None:
    got = source.latest()
    if got is None:
        return
    pixels, index = got
    if index == gl.shown or tuple(np.shape(pixels)[:2]) != (gl.size[1], gl.size[0]):
        return
    gl.result.write(np.ascontiguousarray(pixels, dtype=np.uint8))
    gl.shown = index


def _submit(chain, gl: Gl, source: Any, src: moderngl.Texture, name: str) -> None:
    """`src` copied 1:1 into the RGBA8 target, read back once, handed over."""
    ctx = chain.ctx
    copy = chain._copy
    gl.fbo.use()
    ctx.viewport = (0, 0, *gl.size)
    ctx.disable(moderngl.BLEND)
    src.use(location=0)
    for k, v in (("u_scaled", 0), ("u_origin", (0, 0))):
        if k in copy:
            copy[k].value = v
    chain._copy_vao.render(moderngl.TRIANGLES, vertices=3)
    buf = gl.buffer(source)
    gl.fbo.read_into(buf, components=4)
    gl.submits += 1
    source.submit(buf, gl.submits, params_of(chain.state.values.get(name, {})))
