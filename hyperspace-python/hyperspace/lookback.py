"""The old look-back's per-frame units, which a load still converts.

The look-back is public parts (a delay keeping its pictures, read by the
Trail and Read effect files, `graphmigrate.lookbacks`), and the dream is an
effect file with a Python half (`shaders/fx/dream.glsl`, `dreamhook.py`,
`graphmigrate.dreams`). What stays here: the look-back's per-frame units,
read as 60 Hz frames: ``dream.decay`` → a fade in seconds, ``dream.every``
→ a gap in seconds (`migrate_values`, `migrate_row`); `loadable.echo_seconds`
runs them on an old file before the ladder, whose last steps make the
look-back and the dream public parts.
"""

from __future__ import annotations

import math
from typing import Any

REF_HZ = 60.0                           # the frame rate the old per-frame units meant
FADE_LO, FADE_HI = 0.02, 10.0           # dream.fade: an echo's half-life, seconds (log)
GAP_LO, GAP_HI = 0.0, 0.25              # dream.gap: seconds between captures (0 = every frame)
OLD_DECAY = 0.95                        # the per-frame decay's old default, for a row with no base


# ---- the old per-frame units ----

def fade_of_decay(decay: float, hz: float = REF_HZ) -> float:
    """The half-life, in seconds, of a per-frame `decay` at `hz`: the
    seconds after which decay^(age·hz) is one half. Rounded to 4 places,
    clamped to the fader (a decay of 1 never fades: the longest fade)."""
    d = float(decay)
    if not math.isfinite(d):
        raise ValueError(f"decay {decay!r} is not a number")
    if d >= 1.0:
        return FADE_HI
    if d <= 0.0:
        return FADE_LO
    return round(min(max(math.log(0.5) / (hz * math.log(d)), FADE_LO), FADE_HI), 4)


def decay_per_frame(fade: float, hz: float = REF_HZ) -> float:
    """What a half-life of `fade` seconds fades an echo per frame at `hz`."""
    return 0.5 ** (1.0 / (max(float(fade), 1e-9) * hz))


def gap_of_every(every: float, hz: float = REF_HZ) -> float:
    """Every `every` frames at `hz`, in seconds between captures."""
    e = float(every)
    if not math.isfinite(e):
        raise ValueError(f"every {every!r} is not a number")
    return round(min(max(e / hz, GAP_LO), GAP_HI), 6)


# old id → (new id, the value's conversion)
LEGACY = {"dream.decay": ("dream.fade", fade_of_decay),
          "dream.every": ("dream.gap", gap_of_every)}


def fade_norm(fade: float) -> float:
    """dream.fade's fader position (log over FADE_LO…FADE_HI)."""
    f = min(max(float(fade), FADE_LO), FADE_HI)
    return math.log(f / FADE_LO) / math.log(FADE_HI / FADE_LO)


def migrate_values(values: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """`values` with the per-frame look-back ids read as 60 Hz frames and
    written in seconds (LEGACY), in place in the order; a new id the dict
    already names wins over the old one. Returns (the values, a note per
    id converted); the dict itself when there was nothing to convert."""
    if not any(k in LEGACY for k in values):
        return values, []
    out: dict[str, Any] = {}
    notes = []
    for k, v in values.items():
        if k in LEGACY:
            new, conv = LEGACY[k]
            if new in values:
                notes.append(f"{k} dropped: {new} is named")
                continue
            try:
                out[new] = conv(v)
            except (TypeError, ValueError):
                notes.append(f"{k} {v!r} is not a number, dropped")
                continue
            notes.append(f"{k} {v} → {new} {out[new]}")
        else:
            out[k] = v
    return out, notes


def migrate_row(row: dict, values: dict[str, Any] | None = None) -> tuple[dict, str | None]:
    """A route or desk row (its JSON) on an old per-frame id, on the new
    one. A push on ``dream.decay`` keeps its reach: its depth is re-drawn
    so the same hand throw spans the same decays, read at the base the
    file gives (`values`, the old or new id) or the default. Returns (the
    row, a note or None); the row itself when it was not on an old id."""
    target = row.get("target")
    if target not in LEGACY:
        return row, None
    new = LEGACY[target][0]
    out = dict(row, target=new)
    note = f"{target} → {new}"
    if target == "dream.decay" and out.get("op") == "push":
        # a push at the default depth (1) has no "value" key in its file
        depth = out.get("value", 1.0)
        new_depth = fade_depth(depth, out.get("source"), values)
        if new_depth is None:
            note += f" (push {depth!r} left as it was: not a number)"
        else:
            out["value"] = new_depth
            note += f" (push {float(depth):+g} → {new_depth:+g})"
    return out, note


def old_decay_base(values: dict[str, Any] | None) -> float:
    """The per-frame decay a file's pushes on ``dream.decay`` were drawn
    about: its ``dream.fade`` or ``dream.decay``, else the old default —
    a value that is not a number counts as the default."""
    vals = values or {}
    try:
        if "dream.fade" in vals:
            base = decay_per_frame(float(vals["dream.fade"]))
        else:
            base = float(vals.get("dream.decay", OLD_DECAY))
    except (TypeError, ValueError, ZeroDivisionError, OverflowError):
        return OLD_DECAY
    return base if math.isfinite(base) else OLD_DECAY


def fade_depth(depth, source, values: dict[str, Any] | None = None) -> float | None:
    """A push depth on ``dream.decay`` (its linear 0–1 norm) as one on
    ``dream.fade`` spanning the same decays, about the file's base
    (`old_decay_base`); None when `depth` is not a number. A push adds
    depth · (u − rest): on a height (rest 0) the throw spans base … base +
    depth, on a centred axis base ± depth / 2."""
    try:
        depth = float(depth)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(depth):
        return None
    base = old_decay_base(values)
    height = str(source or "").endswith(".y")
    a, b = (base, base + depth) if height else (base - depth / 2, base + depth / 2)
    a, b = (min(max(x, 1e-6), 1.0) for x in (a, b))
    return round(fade_norm(fade_of_decay(b)) - fade_norm(fade_of_decay(a)), 4)
