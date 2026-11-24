"""Plan 67, rule 5 ("a convenience is a patch, not a fork"): Blocks is
`cells → waveform → cell action ← cells.2 → displace`, and that
patch draws every Blocks look as `blocks.glsl` does — so Blocks can be taken
apart and rebuilt from primitives, and the file stays for speed (one pass
instead of five) and for saved looks, which it keeps drawing byte for byte.

**What is exact.** The grid is one piece (`_lib.glsl`'s `cell_of` and
`cell_pair`), the cell's number is the same function of the block, and the
waveform over it is the same arithmetic (`x − t + ¼` in both).

**What is up to rounding.** Blocks counts its grid in pixels (`Cell`) and the
Measure in frame heights (`Scale`), so where a cell's edge falls exactly on a
pixel's centre (an odd number of pixels to a cell: Aspect 1/16 of 48 is 3) the
two may round that pixel into either cell (`blockspatch.on_edges`). Off the
edges, Blocks works an action out in pixels and divides by the frame's height
once at the end; the patch carries the place in the cell and the cell's size
in frame heights and acts on those — the same arithmetic in another order, an
ulp or two apart. On Mesa's llvmpipe: 349 of 396 renders byte for byte; off the
edges, the rest one level on at most 26 pixels of 6144. The bounds held: off the
edges, one level, on at most one pixel in 200, in at most one render in 8.

Held twice: one pass per node over every Blocks choice and pair of choices at
three times (`FxChain.run_one`, a float32 field between each), and through the
real renderer and graph for every saved Blocks look in `presets/distort/`."""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pytest

from hyperspace.fx import FxChain, FxState

sys.path.insert(0, str(Path(__file__).parent))
from blockspatch import NODES, WIRES, blocks_patch, on_edges

moderngl = pytest.importorskip("moderngl")

W, H = 96, 64
TIMES = (0.0, 0.41, 2.7)


def _picture():
    rng = np.random.default_rng(23)
    pic = rng.integers(0, 256, (H, W, 4), dtype=np.uint8)
    pic[..., 3] = 255
    return pic


def _looks():
    """Every choice of Blocks, every pair of choices, three values of each knob."""
    spec = FxState().specs["blocks"]
    out = [{}]
    choices = [p for p in spec.params if p.choices]
    for p in spec.params:
        if p.choices:
            out += [{p.key: k} for k in range(len(p.choices))]
        else:
            out += [{p.key: round(v) if p.integer else v}
                    for v in (p.lo + (p.hi - p.lo) * f for f in (0.0, 0.37, 1.0))]
    for a, b in itertools.combinations(choices, 2):
        out += [{a.key: i, b.key: j} for i in range(len(a.choices)) for j in range(len(b.choices))]
    # every action with a smaller grid, Group, Aspect and Split: more edges to land on
    out += [{"action": k, "cell": 12.0, "group": 2, "aspect": 1.7, "split": 0.5, "amount": 1.3}
            for k in range(6)]
    return out


def _tex(ctx, dtype="f4", data=None):
    return ctx.texture((W, H), 4, data, dtype=dtype)


def _read(fbo):
    return np.frombuffer(fbo.read(components=4), np.uint8).reshape(H, W, 4).copy()


def test_every_blocks_look_is_the_patch_up_to_rounding(ctx):
    pic = _picture()
    src = _tex(ctx, "f1", pic.tobytes())
    looks = _looks()
    assert len(looks) >= 100
    differ = []
    fields = {k: ctx.framebuffer(color_attachments=[_tex(ctx)])
              for k in ("number", "place", "wave", "push")}
    a = ctx.framebuffer(color_attachments=[_tex(ctx, "f1")])
    b = ctx.framebuffer(color_attachments=[_tex(ctx, "f1")])
    for look in looks:
        bst = FxState()
        bst.values["blocks"].update(on=True, mix=1.0, **look)
        v = dict(bst.values["blocks"])
        pst = FxState()
        pst.set_instances({"cells": 2})
        for name, vals in blocks_patch(v, H).items():
            pst.values[name].update(vals)
        bch, pch = FxChain(ctx, bst), FxChain(ctx, pst)
        for t in TIMES:
            bch.run_one("blocks", src, a, t, opaque=1)
            pch.run_one("cells", src, fields["number"], t, opaque=1, res=(W, H))
            pch.run_one("cells.2", src, fields["place"], t, opaque=1, res=(W, H))
            pch.run_one("waveform", fields["number"].color_attachments[0], fields["wave"], t,
                        opaque=1)
            pch.run_one("cellaction", fields["wave"].color_attachments[0], fields["push"], t,
                        opaque=1, field=fields["place"].color_attachments[0])
            pch.run_one("displace", src, b, t, opaque=1,
                        field=fields["push"].color_attachments[0])
            assert bch.errors == {} and pch.errors == {} and ctx.error == "GL_NO_ERROR"
            ra, rb = _read(a), _read(b)
            diff = np.where(on_edges(v, W, H), 0, np.abs(ra.astype(int) - rb).max(axis=2))
            if diff.any():
                differ.append((look, t, int(diff.max()), int((diff > 0).sum())))
        bch.release()
        pch.release()
    src.release()
    total = len(looks) * len(TIMES)
    for look, t, most, n in differ:
        assert most <= 1 and n <= W * H // 200, (look, t, most, n)
    assert len(differ) <= total // 8, f"{len(differ)} of {total} not byte for byte: {differ[:5]}"


DISTORT = Path(__file__).resolve().parents[1] / "loadable" / "distort"   # (main's #482 moved them)
SAVED = sorted(p for p in DISTORT.glob("*.json")
               if any(k.startswith("fx.blocks.") for k in json.loads(p.read_text())["values"]))


@pytest.mark.parametrize("path", SAVED, ids=lambda p: p.stem)
def test_a_saved_blocks_look_draws_the_same_as_its_patch(ctx, path):
    """The look's Blocks values through the real renderer: `scene → blocks →
    output 1`, and the patch in its place, three frames each."""
    from test_field_wire import _views
    from test_graph_faces import _faces, _px

    from hyperspace import graph as G
    from hyperspace.render import Renderer

    saved = {k[len("fx.blocks."):]: v for k, v in json.loads(path.read_text())["values"].items()
             if k.startswith("fx.blocks.")}

    def frames(nodes, wires, values, instances=None):
        r = Renderer(ctx)
        r.ghost.state.on = False
        section = {"frame": "wired", "nodes": nodes,
                   "wires": [{"from": "shape", "to": "scene.geometry"},
                             {"from": "pattern", "to": "shape.faces"}, *wires]}
        spec = G.read_graph(section, effects=set(r.fx.state.specs))
        assert not spec.notes, spec.notes
        if instances:
            r.fx.state.set_instances(instances)
        r.wiring = spec.wiring()
        for name, v in values.items():
            r.fx.state.values[name].update(v)
        vs = _views(ctx, 1)
        out = []
        for k in range(3):
            r.draw_outputs(_faces(), 160, 120, 1.0, vs, t_now=2.0 + k * 0.37)
            out.append(_px(vs[0].target))
        return out

    blocks = FxState()
    blocks.values["blocks"].update({**saved, "on": True})
    v = dict(blocks.values["blocks"])
    file = frames([{"kind": "effect", "file": "blocks"}],
                  [{"from": "scene", "to": "blocks.image"},
                   {"from": "blocks", "to": "output.1.image"}],
                  {"blocks": v})
    patch = frames(NODES, [*WIRES, {"from": "scene", "to": "displace.image"},
                           {"from": "displace", "to": "output.1.image"}],
                   blocks_patch(v, 120), instances={"cells": 2})
    edges = on_edges(v, 160, 120)
    for k, (a, b) in enumerate(zip(file, patch, strict=True)):
        d = np.where(edges, 0, np.abs(a.astype(int) - b).max(axis=2))
        assert d.max() <= 1 and (d > 0).sum() <= d.size // 200, (
            path.stem, k, int(d.max()), int((d > 0).sum()))


def test_the_saved_looks_are_found():
    """An empty list skips every saved look in silence (the move of the
    distort patches did, once)."""
    assert len(SAVED) >= 5, DISTORT
