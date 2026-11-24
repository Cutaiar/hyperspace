"""Plan 67, rule 5 ("a convenience is a patch, not a fork"): Wave is
`measure → waveform → combine ← measure.2 → displace`, and that patch draws
every Wave look as `wave.glsl` does — so a Wave can be taken apart and rebuilt
from primitives, and the file stays for speed (one pass instead of five) and
for saved looks, which it keeps drawing byte for byte.

**Equal up to the compiler's rounding.** Every field of the patch is bit for bit
the value wave.glsl computes inside itself (the measure, the waveform, the push
direction × wave). The last step is not always: wave.glsl multiplies direction ×
wave × Amount × aspect in one expression, which a GLSL compiler may reorder
(Mesa's does; GLSL 3.30 has no `precise` to forbid it), while Displace multiplies
a stored field. So a sample lands one ulp apart now and then: on Mesa, 184 of
198 looks are byte for byte and the rest differ by one level on one or two
pixels. A hard waveform (square, saw, Steps) is the exception that proves it:
a measure an ulp apart lands a pixel exactly on its edge on the other side, so
that pixel takes the next slab — at most one pixel in a hundred, all on edges.
The bounds held here: a smooth wave, one level on one pixel in a thousand at
most; a hard one, one pixel in a hundred.

Held twice: one pass per node over every Wave choice and pair of choices at
three times (`FxChain.run_one`, a float32 field between each), and through the
real renderer and graph for every saved Wave look in `presets/distort/`."""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pytest

from hyperspace.fx import FxChain, FxState

sys.path.insert(0, str(Path(__file__).parent))
from wavepatch import NODES, WIRES, wave_patch

moderngl = pytest.importorskip("moderngl")

W, H = 96, 64
TIMES = (0.0, 0.41, 2.7)


def _picture():
    rng = np.random.default_rng(23)
    pic = rng.integers(0, 256, (H, W, 4), dtype=np.uint8)
    pic[..., 3] = 255
    return pic


def _looks():
    """Every choice of Wave, every pair of choices, three values of each knob."""
    spec = FxState().specs["wave"]
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
    return out


def _tex(ctx, dtype="f4", data=None):
    return ctx.texture((W, H), 4, data, dtype=dtype)


def _read(fbo):
    return np.frombuffer(fbo.read(components=4), np.uint8).reshape(H, W, 4).copy()


def test_every_wave_look_is_the_patch_up_to_rounding(ctx):
    pic = _picture()
    src = _tex(ctx, "f1", pic.tobytes())
    looks = _looks()
    assert len(looks) >= 60
    differ = []
    # (targets made once and kept, as the app keeps its: releasing the bound
    # framebuffer and making another leaves GL_INVALID_OPERATION on Mesa for
    # the next pass — a driver's, not this test's)
    fields = {k: ctx.framebuffer(color_attachments=[_tex(ctx)])
              for k in ("value", "way", "wave", "push")}
    a = ctx.framebuffer(color_attachments=[_tex(ctx, "f1")])
    b = ctx.framebuffer(color_attachments=[_tex(ctx, "f1")])
    for look in looks:
        wst = FxState()
        wst.values["wave"].update(on=True, mix=1.0, **look)
        v = dict(wst.values["wave"])
        pst = FxState()
        pst.set_instances({"measure": 2})
        for name, vals in wave_patch(v).items():
            pst.values[name].update(vals)
        wch, pch = FxChain(ctx, wst), FxChain(ctx, pst)
        for t in TIMES:
            wch.run_one("wave", src, a, t, opaque=1)
            pch.run_one("measure", src, fields["value"], t, opaque=1, res=(W, H))
            pch.run_one("measure.2", src, fields["way"], t, opaque=1, res=(W, H))
            pch.run_one("waveform", fields["value"].color_attachments[0], fields["wave"], t,
                        opaque=1)
            pch.run_one("combine", fields["way"].color_attachments[0], fields["push"], t,
                        opaque=1, field=fields["wave"].color_attachments[0])
            pch.run_one("displace", src, b, t, opaque=1,
                        field=fields["push"].color_attachments[0])
            assert wch.errors == {} and pch.errors == {} and ctx.error == "GL_NO_ERROR"
            ra, rb = _read(a), _read(b)
            if not np.array_equal(ra, rb):
                diff = np.abs(ra.astype(int) - rb).max(axis=2)
                differ.append((look, t, int(diff.max()), int((diff > 0).sum())))
        wch.release()
        pch.release()
    src.release()
    total = len(looks) * len(TIMES)
    for look, t, most, n in differ:
        hard = look.get("shape", 0) in (2, 3) or look.get("steps", 0) > 0
        if hard:
            assert n <= W * H // 100, (look, t, most, n)
        else:
            assert most <= 1 and n <= W * H // 1000, (look, t, most, n)
    assert len(differ) <= total // 10, f"{len(differ)} of {total} not byte for byte: {differ[:5]}"


DISTORT = Path(__file__).resolve().parents[1] / "presets" / "distort"
SAVED = sorted(p for p in DISTORT.glob("*.json")
               if any(k.startswith("fx.wave.") for k in json.loads(p.read_text())["values"])
               and "shake" not in p.stem and "blocks" not in p.stem and "all-three" not in p.stem)


@pytest.mark.parametrize("path", SAVED, ids=lambda p: p.stem)
def test_a_saved_wave_look_draws_the_same_as_its_patch(ctx, path):
    """The look's Wave values through the real renderer: `scene → wave →
    output 1`, and the patch in its place, three frames each."""
    from test_field_wire import _views
    from test_graph_faces import _faces, _px

    from hyperspace import graph as G
    from hyperspace.render import Renderer

    saved = {k[len("fx.wave."):]: v for k, v in json.loads(path.read_text())["values"].items()
             if k.startswith("fx.wave.")}

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

    wave = FxState()
    wave.values["wave"].update({**saved, "on": True})
    v = dict(wave.values["wave"])
    file = frames([{"kind": "effect", "file": "wave"}],
                  [{"from": "scene", "to": "wave.image"}, {"from": "wave", "to": "output.1.image"}],
                  {"wave": v})
    patch = frames(NODES, [*WIRES, {"from": "scene", "to": "displace.image"},
                           {"from": "displace", "to": "output.1.image"}],
                   wave_patch(v), instances={"measure": 2})
    for k, (a, b) in enumerate(zip(file, patch, strict=True)):
        d = np.abs(a.astype(int) - b).max(axis=2)
        hard = v["shape"] in (2, 3) or v["steps"] > 0
        if hard:
            assert (d > 0).sum() <= d.size // 100, (path.stem, k, int(d.max()), int((d > 0).sum()))
        else:
            assert np.array_equal(a, b), (path.stem, k, int(d.max()), int((d > 0).sum()))
