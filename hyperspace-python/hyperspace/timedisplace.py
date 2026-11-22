"""Time Displace's Python half (plan 66 stage 3a): `shaders/fx/timedisplace.glsl`
says `// @hook timedisplace`, so `fx.FxChain.run_one` hands its pass here.

Each pixel of the effect reads the past at `now − field × Span`; the shader
makes the field and walks the frames. What a fragment shader cannot reach is
the past itself: a look-back's ring (`lookback.Lookback`), which the renderer
keeps by name and hands its chain (`FxChain.rings`, the renderer's own dict).
This module finds the ring the effect's **Look-back** knob names (1 is
`lookback`, n `lookback.<n>`: `ring_name`), binds its atlas on `RING_UNIT`,
and uploads every frame the ring holds, newest first — its slot's origin in
the atlas and its age in seconds on the ring's own clock
(`Lookback.frames`) — then draws the pass.

The pass runs before this frame's capture (every effect does: a capture runs
after every picture an output shows), so it reads what an echo node reads.
With no such ring, a ring that holds nothing yet, or one being remade for a
`dream.res` change, `u_ring_n` is 0 and the pass is its input: a chain of its
own (the previews', the thumbnails' card) has no rings and shows the input.

It keeps no GL objects of its own and no state: the atlas is the ring's.
"""

from __future__ import annotations

from typing import Any, cast

import moderngl
import numpy as np

MAX_ECHOES = 32         # lookback.MAX_ECHOES: the ring's slots (a test holds the two equal)
RING_UNIT = 2           # the texture unit of the atlas (0 the input, 1 the aux)


def ring_name(n: int) -> str:
    """The look-back the knob's `n` names: 1 `lookback`, n ≥ 2 `lookback.<n>`."""
    n = int(n)
    return "lookback" if n <= 1 else f"lookback.{n}"


def ring_of(chain, values: dict):
    """The ring this instance reads, or None: no rings on this chain (a chain
    of its own), or no look-back of that name in the frame's graph."""
    rings = getattr(chain, "rings", None)
    if not rings:
        return None
    return rings.get(ring_name(round(float(values.get("ring", 1)))))


def frames_of(lb) -> list[tuple[int, float]]:
    """(slot, age in seconds) of every frame `lb` holds now, newest first;
    [] for no ring, no atlas, or a ring about to be made again."""
    if lb is None or getattr(lb, "atlas", None) is None:
        return []
    if lb.remaking():
        return []
    return lb.frames()[:MAX_ECHOES]


def advance(spec, values: dict, dt: float) -> None:
    """No drives: its one moving part is a `@clock` fx.py integrates."""


def _set(prog: moderngl.Program, name: str, value) -> None:
    if name in prog:
        cast(moderngl.Uniform, prog[name]).value = value


def _write(prog: moderngl.Program, name: str, data: bytes) -> None:
    if name in prog:
        cast(moderngl.Uniform, prog[name]).write(data)


def run(chain, name: str, prog: moderngl.Program, vao: moderngl.VertexArray,
        src: moderngl.Texture, dst: moderngl.Framebuffer) -> None:
    """The pass, every uniform of the file set by `run_one`: the ring's
    atlas and its frames bound, then drawn into `dst`'s viewport."""
    lb: Any = ring_of(chain, chain.state.values[name])
    held = frames_of(lb)
    _set(prog, "u_ring_n", len(held))
    if held:
        ages = np.zeros(MAX_ECHOES, dtype="f4")
        offs = np.zeros(MAX_ECHOES, dtype="f4")
        for i, (slot, age) in enumerate(held):
            ages[i], offs[i] = max(float(age), 0.0), slot / MAX_ECHOES
        lb.atlas.use(location=RING_UNIT)
        _set(prog, "u_ring_tex", RING_UNIT)
        _write(prog, "u_ring_age", ages.tobytes())
        _write(prog, "u_ring_off", offs.tobytes())
        _set(prog, "u_ring_slot", 1.0 / MAX_ECHOES)
        _set(prog, "u_ring_pad", 0.5 / max(int(lb.echo[1]), 1))
    vao.render(moderngl.TRIANGLES, vertices=3)
