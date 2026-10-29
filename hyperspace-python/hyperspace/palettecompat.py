"""The palette's old ids read as its slice (plan 30 N8, the owner 2026-10-20).

Plan 24 C6's palette folded every hue onto ``centre`` ± ``width``/2 and
rescaled saturation and value into ``sat_lo``–``sat_hi`` and
``val_lo``–``val_hi``. Since N8 it compresses the HSV cylinder into a
closed slice: ``hue_from`` → ``hue_to`` turned by ``hue_turn``,
``sat_from`` → ``sat_to``, ``val_from`` → ``val_to``. A document saved
before carries the old ids; `palette_slice` reads it in the new ones, on
every load (like plan 26 A2's camera.pan, `params.pan_world`: silent, and
the next save writes the new keys), so the look comes back:

- **values**: ``hue_from`` = centre − width/2 and ``hue_to`` = centre +
  width/2, wrapped into 0–360 (centre 200, width 60 → 170 → 230; width
  360 → 0 → 360), ``hue_turn`` 0 — or, when something sets the centre
  outright (a ``position`` route or a macro's base subscriber on it), the
  arc about 0 and ``hue_turn`` = centre, so the centre *is* the turn and
  those rows move to it as they are; ``_lo``/``_hi`` → ``_from``/``_to``.
- **routes and desk rows**: a rename moves the row; any row on the centre
  goes to ``hue_turn`` (it wraps as the centre did, so a hand sweeping
  the hue keeps the arc's width); a push on the width becomes half of it
  apart on each end; any other row on the width is kept dormant, with a
  note.
- **macros**: a subscriber follows its param or its route — a depth
  subscriber on a width push split into one per end (its from / to scale
  each end's half alike); a base subscriber on the width converted when
  both ends stay inside 0–360 over its travel, else dropped with a note.

A leaf: it imports nothing from the package (`library` and `preset` call
it on plain dicts).
"""

from __future__ import annotations

import copy
import re

RENAMED = {"sat_lo": "sat_from", "sat_hi": "sat_to", "val_lo": "val_from", "val_hi": "val_to"}
OLD = re.compile(r"^(fx\.palette(?:\.\d+)?)\.(centre|width|sat_lo|sat_hi|val_lo|val_hi)$")
FOLD_EXACT = 180.0      # a slice up to this wide is the old fold to the bit (palette.glsl)
_ROWS = ("routes", "desk")


def _num(v) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _subs(doc: dict) -> list[dict]:
    macros = doc.get("macros")
    if not isinstance(macros, dict):
        return []
    return [s for m in macros.values() if isinstance(m, dict)
            for s in (m.get("subs") or []) if isinstance(s, dict)]


def _sub_target(s: dict) -> str:
    dep = s.get("depth")
    return str(dep.get("target", "")) if isinstance(dep, dict) else str(s.get("base", ""))


def palette_slice(doc: dict) -> tuple[dict, list[str]]:
    """`doc` (a whole preset, or an `fx` module preset) with its palette ids
    in the slice's form. Returns (a copy, notes); the document itself and
    no notes when it names no old id."""
    values = doc.get("values") if isinstance(doc.get("values"), dict) else {}
    rows = [r for key in _ROWS if isinstance(doc.get(key), list)
            for r in doc[key] if isinstance(r, dict)]
    if not (any(OLD.match(k) for k in values)
            or any(OLD.match(str(r.get("target", ""))) for r in rows)
            or any(OLD.match(_sub_target(s)) for s in _subs(doc))):
        return doc, []
    out = copy.deepcopy(doc)
    notes: list[str] = []
    vals = out.get("values") if isinstance(out.get("values"), dict) else {}
    out_rows = [r for key in _ROWS if isinstance(out.get(key), list)
                for r in out[key] if isinstance(r, dict)]
    subs = _subs(out)
    pres = {m[1] for m in map(OLD.match, [*vals, *(str(r.get("target", "")) for r in out_rows),
                                          *(_sub_target(s) for s in subs)]) if m}
    centres: dict[str, float] = {}     # pre → the centre the document's slice sits at
    for pre in sorted(pres):
        for old, new in RENAMED.items():
            if f"{pre}.{old}" in vals:
                v = vals.pop(f"{pre}.{old}")
                vals.setdefault(f"{pre}.{new}", v)
        named = f"{pre}.centre" in vals or f"{pre}.width" in vals
        c = _num(vals.pop(f"{pre}.centre", 0.0))
        w = _num(vals.pop(f"{pre}.width", 360.0))
        c = 0.0 if c is None else c % 360.0
        w = 360.0 if w is None else min(max(w, 0.0), 360.0)
        # the centre set outright by something: it becomes the turn
        outright = any(str(r.get("target")) == f"{pre}.centre" and r.get("op", "push") != "push"
                       for r in out_rows) or any(s.get("base") == f"{pre}.centre" for s in subs)
        at = 0.0 if outright else c
        centres[pre] = at
        if not (named or outright):
            continue        # only rows or subscribers name it: its values stay as they are
        if w >= 360.0:
            lo, hi = 0.0, 360.0
        else:
            lo, hi = round((at - w / 2) % 360.0, 6), round((at + w / 2) % 360.0, 6)
        vals.setdefault(f"{pre}.hue_from", lo)
        vals.setdefault(f"{pre}.hue_to", hi)
        if outright:
            vals.setdefault(f"{pre}.hue_turn", round(c, 6))
        # a look that changes is said — only when the palette shows it
        # (on, mix above 0, compressing) or a row may bring it in
        shows = (bool(vals.get(f"{pre}.on")) and (_num(vals.get(f"{pre}.mix")) or 0.0) > 0.0) \
            or any(str(r.get("target", "")).startswith(f"{pre}.") for r in out_rows)
        if shows and int(_num(vals.get(f"{pre}.mode", 0)) or 0) == 0 and w > FOLD_EXACT:
            if w >= 360.0:
                notes.append(f"{pre}: the old fold doubled the whole wheel; its slice 0 → 360 "
                             "now leaves the colours as they are")
            else:
                notes.append(f"{pre}: a fold {w:.0f}° wide reads as a wider slice now (the fold "
                             f"holds to {FOLD_EXACT:.0f}°)")
    # the rows: each row on an old id moves to its new one
    for key in _ROWS:
        if not isinstance(out.get(key), list):
            continue
        new_rows: list = []
        for r in out[key]:
            m = OLD.match(str(r.get("target", ""))) if isinstance(r, dict) else None
            if m is None:
                new_rows.append(r)
                continue
            pre, old = m.groups()
            if old in RENAMED:
                new_rows.append({**r, "target": f"{pre}.{RENAMED[old]}"})
            elif old == "centre":
                new_rows.append({**r, "target": f"{pre}.hue_turn"})
            elif r.get("op", "push") == "push" and _num(r.get("value", 0.0)) is not None:
                v = _num(r.get("value", 0.0))
                new_rows.append({**r, "target": f"{pre}.hue_from", "value": -v / 2})
                new_rows.append({**r, "target": f"{pre}.hue_to", "value": v / 2})
            else:
                new_rows.append(r)      # dormant: no slice param takes it whole
                notes.append(f"{r.get('source')} → {pre}.width ({r.get('op')}): the palette "
                             "has no width now; set the slice's ends")
        out[key] = new_rows
    # the macros: each subscriber follows its param or its route
    macros = out.get("macros") if isinstance(out.get("macros"), dict) else {}
    for mid, mac in macros.items():
        if not isinstance(mac, dict) or not isinstance(mac.get("subs"), list):
            continue
        new_subs: list = []
        for s in mac["subs"]:
            m = OLD.match(_sub_target(s)) if isinstance(s, dict) else None
            if m is None:
                new_subs.append(s)
                continue
            pre, old = m.groups()
            dep = s.get("depth")
            if isinstance(dep, dict):
                if old in RENAMED:
                    new_subs.append({**s, "depth": {**dep, "target": f"{pre}.{RENAMED[old]}"}})
                elif old == "centre":
                    new_subs.append({**s, "depth": {**dep, "target": f"{pre}.hue_turn"}})
                else:       # the width push was split: its depth scales both halves
                    new_subs.append({**s, "depth": {**dep, "target": f"{pre}.hue_from"}})
                    new_subs.append({**s, "depth": {**dep, "target": f"{pre}.hue_to"}})
                continue
            if old in RENAMED:
                new_subs.append({**s, "base": f"{pre}.{RENAMED[old]}"})
            elif old == "centre":
                new_subs.append({**s, "base": f"{pre}.hue_turn"})   # the centre is the turn
            else:
                # the width's travel w(x) = from + x·(to − from), in its norm: each
                # end at centre ∓ w/2, kept only while both stay inside 0–360
                a, b = _num(s.get("from", 0.0)), _num(s.get("to", 1.0))
                at = centres.get(pre, 0.0)
                ends = None if a is None or b is None else (
                    ((at - a * 180.0) / 360.0, (at - b * 180.0) / 360.0),
                    ((at + a * 180.0) / 360.0, (at + b * 180.0) / 360.0))
                if ends is not None and all(0.0 <= x <= 1.0 for e in ends for x in e):
                    (f0, f1), (t0, t1) = ends
                    new_subs.append({**s, "base": f"{pre}.hue_from",
                                     "from": round(f0, 6), "to": round(f1, 6)})
                    new_subs.append({**s, "base": f"{pre}.hue_to",
                                     "from": round(t0, 6), "to": round(t1, 6)})
                else:
                    notes.append(f"macro {mid}: its {pre}.width subscriber dropped — the "
                                 "slice's ends would cross 0 / 360; set them in the macro again")
        mac["subs"] = new_subs
    return out, notes
