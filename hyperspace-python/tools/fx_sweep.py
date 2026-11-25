"""Render effect files over a sweep of their knobs; save the bytes, or check them
against a save — the proof that moving a file onto shared pieces (plan 67)
changed nothing.

Every choice, three values of every other knob, every pair of choices, three
times; a speckled picture and a half see-through aux. Keys are the knob values, so a knob added since the save is
skipped, and every render of the save must still be made: `check` renders the
save's own knob values, so a knob whose range has widened since is checked
at the values it was saved at.

    uv run python tools/fx_sweep.py save before.npz [file …]   # on the old code
    uv run python tools/fx_sweep.py check before.npz [file …]  # on the new
"""
import ast
import itertools
import sys

import moderngl
import numpy as np

from hyperspace.fx import FxChain, FxState

FILES = ["wave", "blocks", "displace", "blend", "prism", "zoomblur", "hueturn",
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




def render(ctx, saved=None):
    """Every file's sweep; with `saved` (a save's keys), those knob values."""
    pic, auxp = pictures()
    shots = {}
    for name in FILES:
        st = FxState()
        spec = st.specs[name]
        looks = combos(spec)
        if saved is not None:
            looks = [dict(ast.literal_eval(k.split("|")[1]))
                     for k in dict.fromkeys(k.rsplit("|", 1)[0] for k in saved
                                            if k.split("|")[0] == name)]
        for ci, c in enumerate(looks):
            st2 = FxState()
            st2.values[name].update(on=True, mix=1.0, **c)
            chain = FxChain(ctx, st2)
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
    if mode == "save":
        shots = render(ctx)
        np.savez_compressed(path, **shots)
        print("saved", len(shots))
    else:
        old = np.load(path)
        shots = render(ctx, old.files)
        missing = set(old.files) - set(shots)
        assert not missing, f"{len(missing)} renders of the baseline not made now"
        shots = {k: v for k, v in shots.items() if k in old.files}
        bad = [k for k in shots if not np.array_equal(shots[k], old[k])]
        by = {}
        for k in bad:
            by.setdefault(k.split("|")[0], 0)
            by[k.split("|")[0]] += 1
        print("checked", len(shots), "differ", len(bad), by)
