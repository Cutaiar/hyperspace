"""Plan 90 H3: the dream is an effect file with a Python half
(`shaders/fx/dream.glsl`, `// @hook dream`, `hyperspace/dreamhook.py`).

Drawn through the real renderer with a numpy fake for the worker (torch is
not installed in the cloud): a Colour generator into the dream, the dream
into an output. The fake is synchronous — a submit is answered at once —
so what a frame shows is the answer to the frame before's submit."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

from hyperspace import dreamhook, fx
from hyperspace import graph as G
from hyperspace.fx import FxState

sys.path.insert(0, str(Path(__file__).parent))

moderngl = pytest.importorskip("moderngl")


class Fake:
    """A synchronous dream worker: its answer is `fn` of the submitted
    pixels, at once. `free` says whether it takes a job (`ready`)."""

    def __init__(self, fn=lambda px: 255 - px, free=True):
        self.fn = fn
        self.free = free
        self.jobs: list[tuple[tuple, int, dict]] = []
        self._latest = None

    def ready(self) -> bool:
        return self.free

    def submit(self, frame, frame_index, params=None):
        self.jobs.append((tuple(frame.shape), frame_index, dict(params or {})))
        out = frame.copy()
        out[..., :3] = self.fn(frame[..., :3])
        self._latest = (out, frame_index)

    def latest(self):
        return self._latest


def wired(*pairs, nodes=("colour", "dream"), others=()):
    return {"frame": "wired",
            "nodes": [{"kind": "effect", "file": n} for n in nodes] + list(others),
            "wires": [{"from": a, "to": b} for a, b in pairs]}


DREAM = wired(("colour", "dream.image"), ("dream", "output.1.image"))


def _rig(ctx, section=DREAM, source=None, values=None):
    from hyperspace.render import Renderer

    r = Renderer(ctx)
    r.ghost.state.on = False
    spec = G.read_graph(section, effects=set(FxState().specs))
    assert not spec.notes, spec.notes
    r.wiring = spec.wiring()
    r.fx.dream_source = source
    r.fx.state.values["colour"].update({"on": True, "hue": 0.0, "saturation": 1.0,
                                       "value": 1.0})
    r.fx.state.values["dream"]["on"] = True
    for name, v in (values or {}).items():
        r.fx.state.values[name].update(v)
    return r


def _draw(ctx, r, t, size=(32, 24)):
    from test_graph_faces import _faces, _fbo, _px

    from hyperspace.outputs import Switches, View

    v = View(Switches(), size, target=_fbo(ctx, *size))
    r.draw_outputs(_faces(), *size, 1.0, [v], t_now=t)
    assert ctx.error == "GL_NO_ERROR"
    return _px(v.target)[size[1] // 2, size[0] // 2]


# ---------------------------------------------------------------- the file

def test_the_dream_is_a_hooked_effect_file_making_its_dreamed_picture():
    spec = FxState().specs["dream"]
    assert spec.hook == "dream"
    assert spec.mix == 1.0 and fx.BLENDS[spec.blend] == "mix"     # Q30: the bitmap itself
    keys = {p.key for p in spec.params}
    assert {"k", "layer", "steps", "step", "jitter", "octaves"} <= keys
    k = next(p for p in spec.params if p.key == "k")
    assert k.label == "Hold" and k.default == 1.0                 # Q32: stateless
    layer = next(p for p in spec.params if p.key == "layer")
    assert list(layer.choices) == dreamhook.LAYERS and layer.default == 1   # conv3_3


def test_the_layer_list_is_the_old_one_in_its_stored_order():
    # (a save keeps the index: the old `lookback.LAYERS`, append only)
    assert dreamhook.LAYERS[:6] == ["conv2_2", "conv3_3", "conv4_3", "inception3b",
                                    "inception4c", "inception4e"]
    assert len(dreamhook.LAYERS) == 25 and set(dreamhook.LAYERS) == set(dreamhook.LAYER_INFO)


def test_params_hand_the_worker_its_knobs_by_name():
    got = dreamhook.params_of({"k": 0.05, "layer": 3, "steps": 2, "step": 0.03,
                               "jitter": 8, "octaves": 1})
    assert got == {"k": 0.05, "layer": "inception3b", "steps": 2, "step": 0.03,
                   "jitter": 8, "octaves": 1}


# ---------------------------------------------------------------- through the renderer

def test_with_no_worker_the_picture_passes_through_said(ctx):
    r = _rig(ctx)
    got = _draw(ctx, r, 1.0)
    assert got[0] == 255 and got[1] < 3 and got[2] < 3          # red, untouched
    assert r.fx.said["dream"] == dreamhook.NO_WORKER


def test_the_worker_dreams_the_picture_and_its_answer_is_shown(ctx):
    fake = Fake()
    r = _rig(ctx, source=fake)
    first = _draw(ctx, r, 1.0)
    second = _draw(ctx, r, 1.0 + 1 / 60)
    assert first[0] == 255 and first[1] < 3                    # nothing landed yet: passes
    assert second[0] < 3 and second[1] == 255 and second[2] == 255    # red, inverted: cyan
    shape, _, params = fake.jobs[0]
    assert shape == (24, 32, 4)                                  # at its input's own size
    assert params["layer"] == "conv3_3" and params["k"] == 1.0
    assert "the dream worker's" in r.fx.said["dream"]


def test_its_knobs_go_with_each_submit(ctx):
    fake = Fake()
    r = _rig(ctx, source=fake, values={"dream": {"k": 0.1, "layer": 16, "steps": 3}})
    _draw(ctx, r, 1.0)
    assert fake.jobs[-1][2] == {"k": 0.1, "layer": "conv1", "steps": 3, "step": 0.03,
                                "jitter": 8, "octaves": 0}


def test_it_submits_only_when_the_worker_is_free(ctx):
    fake = Fake(free=False)
    r = _rig(ctx, source=fake)
    for i in range(3):
        _draw(ctx, r, 1.0 + i / 60)
    assert fake.jobs == []
    fake.free = True
    _draw(ctx, r, 2.0)
    assert len(fake.jobs) == 1


def test_off_it_submits_nothing_and_passes_through(ctx):
    fake = Fake()
    r = _rig(ctx, source=fake, values={"dream": {"on": False}})
    got = _draw(ctx, r, 1.0)
    _draw(ctx, r, 1.1)
    assert fake.jobs == [] and got[0] == 255 and got[1] < 3


def test_mix_lays_the_dreamed_picture_back_on_its_input(ctx):
    fake = Fake()
    r = _rig(ctx, source=fake, values={"dream": {"mix": 0.5}})
    _draw(ctx, r, 1.0)
    got = _draw(ctx, r, 1.1)
    np.testing.assert_allclose(got[:3], [128, 128, 128], atol=2)   # red and cyan, halved


def test_after_a_resize_it_dreams_at_the_resized_size(ctx):
    section = wired(("colour", "resize.image"), ("resize", "dream.image"),
                    ("dream", "output.1.image"), others=[{"kind": "resize"}])
    fake = Fake()
    r = _rig(ctx, section, source=fake)
    from hyperspace.view import RESIZE_SIDES

    _draw(ctx, r, 1.0, size=(64, 40))
    w = fake.jobs[0][0][1]
    assert w in RESIZE_SIDES and w != 64          # the resize's own size, not the frame's


def test_one_live_dream_a_second_passes_through_said(ctx):
    section = wired(("colour", "dream.image"), ("dream", "dream.2.image"),
                    ("dream.2", "output.1.image"),
                    nodes=("colour",),
                    others=[{"kind": "effect", "file": "dream"},
                            {"kind": "effect", "file": "dream", "instance": 2}])
    fake = Fake()
    r = _rig(ctx, section, source=fake)
    r.fx.state.set_instances({"dream": 2})
    r.fx.state.values["dream.2"]["on"] = True
    _draw(ctx, r, 1.1)
    _draw(ctx, r, 1.2)
    holders = {r.fx.said.get("dream", ""), r.fx.said.get("dream.2", "")}
    assert any("one live dream" in s for s in holders)
    assert len({j[1] for j in fake.jobs}) == len(fake.jobs) == 2   # one a frame, one dream


def test_the_node_says_what_its_hook_said(ctx):
    r = _rig(ctx)
    _draw(ctx, r, 1.0)
    assert r._graph.nodes["dream"].said == dreamhook.NO_WORKER


def test_a_deck_dreams_when_its_graph_holds_a_dream_on():
    """`deck.dreams` (the lend and the app's banner): any wire end, `output.all`
    included, is read without a fault (found by the app run)."""
    from types import SimpleNamespace as NS

    from hyperspace.deck import dreams

    spec = G.read_graph(wired(("colour", "dream.image"), ("dream", "output.all.image")),
                        effects=set(FxState().specs))
    values = {"dream": {"on": True}}
    deck = NS(graph=NS(spec=spec), renderer=NS(fx=NS(state=NS(values=values))))
    assert dreams(deck)
    values["dream"]["on"] = False
    assert not dreams(deck)
