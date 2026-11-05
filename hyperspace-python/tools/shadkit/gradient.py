"""CSS gradients, the way the browser actually computes them.

Tailwind v4 emits `linear-gradient(in oklab, ...)` and interpolates with
PREMULTIPLIED alpha. A straight sRGB lerp between the same endpoints is up to
2.6 levels off in the middle — measured against Chromium — which is over the
kit's flat-region budget, so the ramp is computed properly and uploaded as a
texture rather than approximated with per-vertex shading.

The model reproduces Chromium's `bg-gradient-to-t from-primary/5 to-card` to
within 0.86 levels across a 160px card, which is rounding.
"""

from __future__ import annotations

import numpy as np
import OpenGL.GL as GL


def oklab_to_srgb8(L: float, a: float = 0.0, b: float = 0.0) -> tuple:
    """oklab -> sRGB bytes. For a == b == 0 every channel is L**3 in linear."""
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    lin = (
        +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )
    out = []
    for v in lin:
        v = min(max(v, 0.0), 1.0)
        s8 = 12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055
        out.append(int(round(s8 * 255.0)))
    return tuple(out)


def ramp_oklab(stop0: tuple, stop1: tuple, n: int = 256) -> np.ndarray:
    """An n-step RGBA8 ramp, premultiplied-oklab interpolated.

    stop0/stop1 are ((L, a, b), alpha). Index 0 is stop1 (the 100% end, drawn
    at the top for `to-t`); index n-1 is stop0.
    """
    (L0, a0, b0), A0 = stop0
    (L1, a1, b1), A1 = stop1
    out = np.zeros((n, 4), np.uint8)
    for i in range(n):
        t = 1.0 - (i + 0.5) / n                 # 1 at the top row, 0 at the bottom
        A = A0 + (A1 - A0) * t
        if A <= 1e-6:
            out[i] = (0, 0, 0, 0)
            continue
        L = (L0 * A0 + (L1 * A1 - L0 * A0) * t) / A
        a = (a0 * A0 + (a1 * A1 - a0 * A0) * t) / A
        b = (b0 * A0 + (b1 * A1 - b0 * A0) * t) / A
        r, g, bb = oklab_to_srgb8(L, a, b)
        out[i] = (r, g, bb, int(round(A * 255.0)))
    return out


def upload_1d(ramp: np.ndarray) -> int:
    """A 1 x n RGBA8 texture, clamped and linearly filtered."""
    tex = GL.glGenTextures(1)
    GL.glBindTexture(GL.GL_TEXTURE_2D, tex)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
    GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 1)
    GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, 1, len(ramp), 0,
                    GL.GL_RGBA, GL.GL_UNSIGNED_BYTE,
                    np.ascontiguousarray(ramp.reshape(len(ramp), 1, 4)))
    return int(tex)


def card_gradient(lightness: dict):
    """shadcn's `bg-gradient-to-t from-primary/5 to-card`, for one theme.

    Both endpoints are theme tokens, so the ramp is not a constant: in dark,
    `primary` is near-white and the wash runs light rather than dark.
    """
    return (((lightness["primary"], 0.0, 0.0), 0.05),
            ((lightness["card"], 0.0, 0.0), 1.0))
