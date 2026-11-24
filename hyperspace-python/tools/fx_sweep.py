"""Render effect files over a sweep of their knobs; save the bytes, or check them
against a save — the proof that moving a file onto shared pieces (plan 67)
changed nothing.

Every choice, three values of every other knob, every pair of choices, three
times; a speckled picture and a half see-through aux; Time Displace with a
filled ring. Keys are the knob values, so a knob added since the save is
skipped, and every render of the save must still be made.

    uv run python tools/fx_sweep.py save before.npz [file …]   # on the old code
    uv run python tools/fx_sweep.py check before.npz [file …]  # on the new
"""
import itertools
import sys

import moderngl
import numpy as np

from hyperspace.fx import FxChain, FxState

FILES = ["wave", "blocks", "displace", "blend", "prism", "zoomblur", "timedisplace", "huecycle",
         "oilslick"]
W, H = 96, 64
TIMES = (0.0, 0.73, 3.1)


def pictures():
    rng = np.random.default_rng(11)
    a = rng.integers(0, 256, (H, W, 4), dtype=np.uint8)
    a[..., 3] = 255
    b = rng.integers(0, 256, (H, W, 4), dtype=np.uint8)
    b[: H // 2, :, 3] = 128
    return a, b


def combos(spec):
    base = {}
    out = [dict(base)]
    for p in spec.params:
        if p.choices:
            for k in range(len(p.choices)):
                out.append({p.key: k})
        else:
            for f in (0.0, 0.37, 1.0):
                v = p.lo + (p.hi - p.lo) * f
                out.append({p.key: round(v) if p.integer else v})
    # a few crossings of every pair of choices
    ch = [p for p in spec.params if p.choices]
    for a, b in itertools.combinations(ch, 2):
        for i in range(len(a.choices)):
            for j in range(len(b.choices)):
                out.append({a.key: i, b.key: j})
    return out


_RING = []


def ring(ctx):
    from hyperspace.lookback import Lookback
    if not _RING:
        lb = Lookback(ctx)
        assert lb._ensure(W, H)
        ew, eh = lb.echo
        rng = np.random.default_rng(5)
        for slot in range(6):
            px = rng.integers(0, 256, (eh, ew, 4), dtype=np.uint8)
            px[..., 3] = 255
            lb.write_slot(slot, px, at=10.0 - 0.9 * (6 - slot))
        lb.clock, lb._ticked = 10.0, True
        _RING.append(lb)
    return _RING[0]


def render(ctx):
    pic, auxp = pictures()
    shots = {}
    for name in FILES:
        st = FxState()
        spec = st.specs[name]
        for ci, c in enumerate(combos(spec)):
            st2 = FxState()
            st2.values[name].update(on=True, mix=1.0, **c)
            chain = FxChain(ctx, st2)
            if name == "timedisplace":
                chain.rings = {"lookback": ring(ctx)}
            src = ctx.texture((W, H), 4, pic.tobytes())
            aux = ctx.texture((W, H), 4, auxp.tobytes())
            out = ctx.framebuffer(color_attachments=[ctx.texture((W, H), 4)])
            for t in TIMES:
                chain.run_one(name, src, out, t, opaque=1, aux=aux)
                assert not chain.errors, chain.errors
                shots[f"{name}|{sorted(c.items())}|{t}"] = np.frombuffer(out.read(components=4), np.uint8).copy()
            for o in (src, aux, out):
                o.release()
            chain.release()
    return shots


if __name__ == "__main__":
    mode, path = sys.argv[1], sys.argv[2]
    if len(sys.argv) > 3:
        FILES[:] = sys.argv[3:]
    ctx = moderngl.create_context(standalone=True)
    shots = render(ctx)
    if mode == "save":
        np.savez_compressed(path, **shots)
        print("saved", len(shots))
    else:
        old = np.load(path)
        missing = set(old.files) - set(shots)
        assert not missing, f"{len(missing)} renders of the baseline not made now"
        shots = {k: v for k, v in shots.items() if k in old.files}
        bad = [k for k in shots if not np.array_equal(shots[k], old[k])]
        by = {}
        for k in bad:
            by.setdefault(k.split("|")[0], 0)
            by[k.split("|")[0]] += 1
        print("checked", len(shots), "differ", len(bad), by)
