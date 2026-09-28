"""The GLSL every shader shares (audit V2).

Two things were written more than once: the fullscreen-triangle vertex
shader every post pass uses (`QUAD_VS`, once in fx.py and once in
lookback.py), and the colour helpers — `hsv`, `pal`, `LUMA`, the hue
rotation — spelled again in `patterns.glsl`, `fx/_lib.glsl` and the
look-back's post shader. They live here now: `QUAD_VS` as a string, the
helpers as `shaders/_common.glsl`, which `common()` reads and the face
program (render.py), every effect (fx.py) and the post pass (lookback.py)
prepend to their own source. Edit the file while the app runs and the
patterns and effects recompile on their usual mtime checks.

The 2-D hashes are deliberately *not* shared: `patterns.glsl`'s cellular
modes were tuned on their own `hash21` / `hash22` and the effects' lib has
a different, GPU-stable pair; making them one would move every cell.
"""

from __future__ import annotations

from pathlib import Path

SHADERS = Path(__file__).parent / "shaders"
COMMON_GLSL = SHADERS / "_common.glsl"

# one triangle over the viewport; v_uv 0..1 across it
QUAD_VS = """
#version 330
out vec2 v_uv;
void main() {
    vec2 p = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
    v_uv = p;
    gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
}
"""


def common() -> str:
    """The shared helpers' source, read fresh (it is user-editable)."""
    try:
        return COMMON_GLSL.read_text()
    except OSError:
        return ""


def common_mtime() -> float:
    try:
        return COMMON_GLSL.stat().st_mtime
    except OSError:
        return 0.0
