"""A delay's stack — the frames before this one, kept (plan 90 H1).

Plan 67 §7.1 made the past one primitive: a stack of T, read at an index or
summed over them. Plan 90 made the delay its one maker (the owner,
2026-11-26: "merge, call it Delay"): a delay of depth 1 is plan 34's z⁻¹,
and a deeper one keeps that many past frames for the readers that take a
stack (`// @takes stack stack`: Read, Trail).

The stack sits beside the delay's half-float pair (`render.DelayPair`) and
never replaces it. The pair paints and swaps exactly as it always has, so a
delay's picture is last frame's whatever its depth, and a saved delay draws
byte for byte. At the frame's turn, a pair that committed a frame hands it
to the stack (`commit`): a GPU copy (`glCopyTexSubImage3D`, core since GL
1.2) of the pair's read side into one layer of a 2D texture array. So:

- a reader never sees this frame (the commit happens at the turn, before
  the graph runs, whatever order its passes take);
- a stack is made only when a reader asks for it (`Renderer.delay_stack`),
  so a delay nobody reads as a stack costs nothing more;
- one sampler holds every entry: a list of 2D textures would need a unit
  each, and the Mac's GL has sixteen.

A texture array, not a 3D texture: GL_MAX_3D_TEXTURE_SIZE is 2048 (a 4K
frame would not fit), and filtering in depth would blend the ring's newest
entry into its oldest at the seam. A read between two entries is two fetches
and a mix, in the reader (`fx.STACK_HEAD`).

Time is the stack's own clock, in seconds, moved once a frame by the
renderer's time (`tick`); a frame whose time did not move counts one frame
at REF_HZ (as the look-back's ring, plan 14 WP6), so a test drawing at one
fixed time still sees frames go by. A frame is kept every `gap` seconds of
that clock (0: every frame), the same rule as the ring's `_due_now`.
"""

from __future__ import annotations

from typing import Any

import moderngl

REF_HZ = 60.0                  # what a frame whose time did not move counts as
MAX_DEPTH = 64                 # the most frames a stack keeps (`view.DELAY_DEPTH`)
# the most every stack together may hold (plan 90 Q4: one budget for them
# all, refused in words past it) — 1 GiB: 32 half-float frames at 1080p
# are 531 MB
BUDGET = 1 << 30
OVER_BUDGET = ("{name}: a stack of {depth} at {w}×{h} is {mb:.0f} MB, past the "
               "{budget:.0f} MB all stacks may hold — fewer frames, or a resize before it")


def frame_bytes(size: tuple[int, int]) -> int:
    """One entry's bytes: RGBA half float, as the delay's pair."""
    return int(size[0]) * int(size[1]) * 8


class DelayStack:
    """One delay's kept frames: a texture array of `depth` layers at the
    pair's size, and `entries`, (layer, clock) newest first."""

    def __init__(self) -> None:
        self.tex: moderngl.TextureArray | None = None
        self.size = (0, 0)
        self.depth = 0
        self.entries: list[tuple[int, float]] = []
        self.clock = 0.0               # seconds (`tick`)
        self._t_last: float | None = None
        self.dt = 1.0 / REF_HZ         # the last tick's step
        self._due: float | None = None # the clock of the next frame kept
        self.idle = 0                  # frames no reader has asked (`Renderer`)
        self.error = ""                # why it holds nothing (a budget, a driver)

    # ---- time ----

    def tick(self, t: float | None) -> None:
        """Once a frame, at the turn: the clock moves by the renderer's
        time since the last tick, or one REF_HZ frame if it did not move."""
        if t is not None and self._t_last is not None and t > self._t_last:
            dt = float(t) - self._t_last
        else:
            dt = 1.0 / REF_HZ
        if t is not None:
            self._t_last = float(t)
        self.dt = dt
        self.clock += dt

    def due(self, at: float, gap: float) -> bool:
        """Whether the frame drawn at clock `at` is kept: one every `gap`
        seconds, the first at once; a frame within half a frame of its due
        time is on time, so a gap of N frames keeps every Nth at any rate."""
        gap = max(float(gap), 0.0)
        dt = self.dt
        if self._due is None:
            self._due = at
        if at + dt / 2 < self._due:
            return False
        self._due += gap
        if self._due <= at + dt / 2 - dt:       # fell behind (a stall): from now
            self._due = at + gap
        return True

    # ---- the frames ----

    def ensure(self, ctx: moderngl.Context, size: tuple[int, int], depth: int) -> bool:
        """The array at `size` and `depth` layers, made again — clean — when
        either changed. False, with the reason on `error`, when it cannot be."""
        size = (int(size[0]), int(size[1]))
        depth = max(1, min(int(depth), MAX_DEPTH))
        if self.tex is not None and size == self.size and depth == self.depth:
            return True
        self.release()
        try:
            tex = ctx.texture_array((size[0], size[1], depth), 4, dtype="f2")
            tex.repeat_x = tex.repeat_y = False
            tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        except Exception as e:  # noqa: BLE001 — no stack this frame, never a stuck one
            self.error = f"no stack at {size[0]}×{size[1]}×{depth}: {e}"[:160]
            return False
        self.tex, self.size, self.depth, self.error = tex, size, depth, ""
        return True

    def commit(self, ctx: moderngl.Context, src: moderngl.Framebuffer, size: tuple[int, int],
               depth: int, gap: float) -> bool:
        """The frame the pair just committed (`src`, its read side at `size`),
        drawn one frame ago, into the stack if it is due. True if kept."""
        at = self.clock - self.dt
        if not self.ensure(ctx, size, depth) or self.tex is None:
            return False
        if not self.due(at, gap):
            return False
        used = {layer for layer, _ in self.entries}
        if len(self.entries) >= self.depth:
            layer = self.entries[-1][0]                   # the oldest goes
            self.entries = self.entries[:-1]
        else:
            layer = next(i for i in range(self.depth) if i not in used)
        copy_layer(src, self.tex, layer, self.size)
        self.entries.insert(0, (layer, at))
        return True

    def reset(self) -> None:
        """Hold nothing (a load, R19): the next commit starts it again."""
        self.entries = []
        self._due = None

    def release(self) -> None:
        if self.tex is not None:
            try:
                self.tex.release()
            except Exception:  # noqa: BLE001, S110 — a lost context: nothing to free
                pass
        self.tex = None
        self.size = (0, 0)
        self.depth = 0
        self.entries = []
        self._due = None

    # ---- what a reader binds ----

    def read(self, depth: int | None = None) -> dict[str, Any] | None:
        """What a reader binds this frame — the array, and per entry newest
        first its layer and its age in seconds, at most `depth` of them — or
        None while it holds nothing."""
        if self.tex is None or not self.entries:
            return None
        n = len(self.entries) if depth is None else max(1, min(int(depth), len(self.entries)))
        got = self.entries[:n]
        return {"tex": self.tex, "layers": [float(layer) for layer, _ in got],
                "ages": [self.clock - at for _, at in got], "size": self.size}


def copy_layer(src: moderngl.Framebuffer, dst: moderngl.TextureArray, layer: int,
               size: tuple[int, int]) -> None:
    """`src`'s colour, `size` from its corner, into layer `layer` of `dst`: one
    GPU copy (`glCopyTexSubImage3D`), the read framebuffer and the array's
    binding put back as they were, so moderngl's own state is untouched."""
    from OpenGL import GL

    w, h = int(size[0]), int(size[1])
    read_was = GL.glGetIntegerv(GL.GL_READ_FRAMEBUFFER_BINDING)
    array_was = GL.glGetIntegerv(GL.GL_TEXTURE_BINDING_2D_ARRAY)
    try:
        GL.glBindFramebuffer(GL.GL_READ_FRAMEBUFFER, src.glo)
        GL.glReadBuffer(GL.GL_COLOR_ATTACHMENT0)
        GL.glBindTexture(GL.GL_TEXTURE_2D_ARRAY, dst.glo)
        GL.glCopyTexSubImage3D(GL.GL_TEXTURE_2D_ARRAY, 0, 0, 0, int(layer), 0, 0, w, h)
    finally:
        GL.glBindTexture(GL.GL_TEXTURE_2D_ARRAY, int(array_was))
        GL.glBindFramebuffer(GL.GL_READ_FRAMEBUFFER, int(read_was))
