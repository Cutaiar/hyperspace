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

A broken edit must not take the show down (the rule patterns.glsl and
the effects already keep): the face program shows the error and draws
no faces, an effect that fails is skipped, and the look-back's post
pass — which every frame goes through, effects or not — falls back to
`FALLBACK`, the copy of the file as shipped, and says so. A test pins
`FALLBACK` to the file in the repo so the two cannot drift.
"""

from __future__ import annotations

import re
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


def gl_error(e: Exception, names: dict[int, str]) -> str:
    """The first compiler message, with the source string it points into
    named: `names` maps a string index (the `#line 1 <n>` the consumer
    emitted) to a prefix, e.g. {1: "_common.glsl:", 2: "line "}."""
    lines = [ln.strip() for ln in str(e).splitlines() if ln.strip()]
    msg = next((ln for ln in lines if "ERROR" in ln.upper()), lines[-1] if lines else str(e))
    for k, name in names.items():
        msg = re.sub(rf"ERROR:\s*{k}:(\d+):", lambda m, name=name: f"{name}{m.group(1)}:", msg)
    return msg[:200]


# the file as shipped — what the post pass compiles against when the
# user's edit does not. tests/test_fx.py holds it equal to the file.
FALLBACK = """\
// Helpers shared by every shader — the face patterns (patterns.glsl), every
// effect in fx/ (after this comes fx/_lib.glsl) and the look-back's post
// pass. Prepended by glsl.py; EDIT WHILE THE APP RUNS and the patterns and
// effects recompile. Nothing here reads a uniform, so it compiles anywhere.

const float PI = 3.14159265359;
const float TAU = 6.28318530718;
const vec3 LUMA = vec3(0.299, 0.587, 0.114);

float luma(vec3 c) { return dot(c, LUMA); }
float peak(vec3 c) { return max(c.r, max(c.g, c.b)); }

mat2 rot(float a) {
    float c = cos(a), s = sin(a);
    return mat2(c, s, -s, c);
}

// hue [0,1), saturation, value → rgb
vec3 hsv2rgb(vec3 c) {
    vec3 k = mod(vec3(5.0, 3.0, 1.0) + c.x * 6.0, 6.0);
    return c.z - c.z * c.y * clamp(min(k, 4.0 - k), 0.0, 1.0);
}
vec3 hsv(float h, float s, float v) { return hsv2rgb(vec3(h, s, v)); }

vec3 rgb2hsv(vec3 c) {
    vec4 K = vec4(0.0, -1.0 / 3.0, 2.0 / 3.0, -1.0);
    vec4 p = mix(vec4(c.bg, K.wz), vec4(c.gb, K.xy), step(c.b, c.g));
    vec4 q = mix(vec4(p.xyw, c.r), vec4(c.r, p.yzx), step(p.x, c.r));
    float d = q.x - min(q.w, q.y);
    return vec3(abs(q.z + (q.w - q.y) / (6.0 * d + 1e-10)), d / (q.x + 1e-10), q.x);
}

// the chroma plane turned about the grey axis (YIQ): luminance is kept
vec3 hue_rotate(vec3 c, float a) {
    float y = dot(c, LUMA);
    float i = dot(c, vec3(0.596, -0.274, -0.322));
    float q = dot(c, vec3(0.211, -0.523, 0.312));
    float ca = cos(a), sa = sin(a);
    float i2 = i * ca - q * sa, q2 = i * sa + q * ca;
    return vec3(y + 0.956 * i2 + 0.621 * q2, y - 0.272 * i2 - 0.647 * q2,
                y - 1.106 * i2 + 1.703 * q2);
}

// cosine palette (iq): a + b·cos(2π(c·t + d)) — smooth colour cycles
// without hue banding. a = base, b = amplitude, c = frequency, d = phase.
vec3 pal(float t, vec3 a, vec3 b, vec3 c, vec3 d) { return a + b * cos(TAU * (c * t + d)); }
"""
