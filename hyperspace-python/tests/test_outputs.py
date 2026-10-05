"""Plan 21: the compose path — a picture per output on one GL context.

The pure half first (`outputs.route`, `outputs.fit`, the module's
imports), then the renderer's half on offscreen targets standing in for
the windows: the default view is today's frame byte for byte, every
switch state shows its picture, the scene pass, the capture and the
hands' layer run once a frame and the effect chain once per distinct
pipeline, and a failing view, pipeline or hands pass never costs the
other views, the first target's binding or the dim.

The pictures are offscreen renders from synthetic hands (fake_hands);
no window, screen or tracker is involved.
"""

from __future__ import annotations

import ast
from pathlib import Path

from hyperspace import outputs as O
from hyperspace.outputs import HANDS, SCENE, SCENE_HANDS, Switches, fit, route

# ---------------------------------------------------------------- no GL


def test_route():
    """Every row of the plan's table ("The frame as it will be"): with the
    through switch off, or no effect on, or no hand shown, the hands go
    over the finished frame or nowhere."""
    for fx_on in (False, True):
        for through in (False, True):
            def r(scene, hands, visible, through=through, fx_on=fx_on):
                return route(Switches(scene=scene, hands=hands, through=through), fx_on, visible)

            # scene on
            assert r(True, False, True) == (SCENE, False)        # hands switch off
            assert r(True, True, False) == (SCENE, False)        # no hand shows
            # scene off
            assert r(False, False, True) == (None, False)
            assert r(False, True, False) == (None, False)
            if not (through and fx_on):
                assert r(True, True, True) == (SCENE, True)      # hands over the effects
                assert r(False, True, True) == (None, True)      # hands alone on the ground
    # the dim never routes
    assert route(Switches(dim=0.0), True, True) == route(Switches(), True, True)
    assert {SCENE, SCENE_HANDS, HANDS} == {0, 1, 2} and O.PIPELINES == (0, 1, 2)
    assert O.MAX_OUTPUTS == 4


def test_fit():
    assert fit((640, 400), (640, 400)) == (0, 0, 640, 400)
    assert fit((1920, 1080), (1280, 720)) == (0, 0, 1280, 720)          # same aspect: scaled
    assert fit((1600, 900), (1600, 1200)) == (0, 150, 1600, 900)        # letterbox: bars top/bottom
    assert fit((1600, 900), (800, 900)) == (0, 225, 800, 450)
    assert fit((900, 1600), (1600, 900)) == (547, 0, 506, 900)          # pillarbox
    x, y, w, h = fit((1920, 1080), (1024, 768))
    assert (w, h) == (1024, 576) and (x, y) == (0, 96)
    assert abs(w / h - 1920 / 1080) < 0.01
    assert fit((0, 0), (300, 200)) == (0, 0, 300, 200)                  # degenerate: the whole
    for src, dst in (((7, 3), (5, 11)), ((1, 1000), (1000, 1))):        # always inside dst
        x, y, w, h = fit(src, dst)
        assert x >= 0 and y >= 0 and w >= 1 and h >= 1 and x + w <= dst[0] and y + h <= dst[1]


def test_a_view_defaults_to_its_whole_size():
    v = O.View(Switches(), (320, 200))
    assert v.rect == (0, 0, 320, 200) and v.error == "" and v.handoff is None
    assert O.View(Switches(), (320, 200), viewport=(5, 6, 100, 50)).rect == (5, 6, 100, 50)
    sw = Switches()
    assert (sw.scene, sw.hands, sw.through, sw.dim) == (True, True, False, 1.0)


def test_outputs_imports_nothing_from_app_ui_or_params():
    """ARCHITECTURE §3: the render stack only reads. outputs.py imports
    moderngl and glsl at most — no app, ui, params, routing or library."""
    tree = ast.parse(Path(O.__file__).read_text())
    banned = {"app", "ui", "params", "routing", "library", "preset", "undo", "control",
              "overlay", "config"}
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.ImportFrom):
            names = [(node.module or "").split(".")[-1]] + [a.name for a in node.names]
        elif isinstance(node, ast.Import):
            names = [a.name.split(".")[-1] for a in node.names]
        assert not banned & set(names), names
        if isinstance(node, ast.ImportFrom) and node.level:
            assert node.module in (None, "glsl"), node.module
