"""Plan 26 A2b — the stroke-space toggle (owner, 2026-10-14).

`view.screen_strokes` off (the default): strokes in world space — the line
width and the point radius are × camera.zoom, the pre-A2 formula, so the
edges and the dots grow and shrink with the shape. On: screen space — A2's
fixed pixel weight. At zoom 1 the two are the same frame byte for byte.
"""

from __future__ import annotations

import json

import numpy as np
import pytest
from test_camera import _draw, _rows, _view, ctx  # noqa: F401  (the GL context fixture)
from test_presets import boot, boot_registry

from hyperspace.geometry import geom, is_3d, view_angles, world_points
from hyperspace.params import part_of
from hyperspace.view import ViewState


def _strokes(ctx, monkeypatch, **kw):  # noqa: F811
    """One draw: what it uploaded (test_camera._rows)."""
    return _rows(ctx, monkeypatch, _view(lines=True, **kw))


def test_the_default_is_world_space_a_preset_performance_switch():
    reg = boot_registry()
    p = reg["view.screen_strokes"]
    assert ViewState().screen_strokes is False and p.base is False
    assert p.group == "view" and part_of(p) == "performance" and p.persist
    assert p.modulatable                      # as view.lines / view.cut_through


def test_the_switch_is_in_a_saved_preset_and_loads_back(tmp_path):
    rig = boot(tmp_path)
    rig.reg["view.screen_strokes"].set(True)
    doc = rig.presets.document("S")
    assert doc["values"]["view.screen_strokes"] is True
    rig.reg["view.screen_strokes"].set(False)
    path = tmp_path / "S.json"
    path.write_text(json.dumps(doc))
    rig.presets.load_doc(doc, path)
    assert rig.view.screen_strokes is True
    # a preset without the key (every corpus file) lands world space
    del doc["values"]["view.screen_strokes"]
    rig.presets.load_doc(doc, path)
    assert rig.view.screen_strokes is False


@pytest.mark.parametrize("lines,points", [(True, True), (True, False), (False, True)])
def test_at_zoom_1_both_modes_draw_the_same_frame(ctx, lines, points):  # noqa: F811
    for shape in (0, 3):
        world, _ = _draw(ctx, _view(shape=shape, lines=lines, points=points, zoom=1.0))
        screen, _ = _draw(ctx, _view(shape=shape, lines=lines, points=points, zoom=1.0,
                                     screen_strokes=True))
        assert np.array_equal(world, screen)


@pytest.mark.parametrize("zoom", [0.5, 2.0])
def test_world_space_scales_the_width_and_radius_by_the_zoom(ctx, monkeypatch, zoom):  # noqa: F811
    """World space is the pre-A2 arithmetic: width × zoom before the 1 px
    floor (the sub-pixel part folded into alpha), radius × zoom before the
    whole-pixel rounding; screen space is the same at every zoom. On one
    copy (the field as it always was) the CPU does it, as before; the
    shaders' own per-copy scaling is off."""
    l1 = _strokes(ctx, monkeypatch, zoom=1.0, bright=1.6)
    ls = _strokes(ctx, monkeypatch, zoom=zoom, bright=1.6, screen_strokes=True)
    lw = _strokes(ctx, monkeypatch, zoom=zoom, bright=1.6)
    assert l1["wscale"] == ls["wscale"] == lw["wscale"] == (0.0, 0.0)
    l1, p1 = l1["lines"], l1["points"]
    ls, ps = ls["lines"], ls["points"]
    lw, pw = lw["lines"], lw["points"]
    # screen space: A2's strokes, whatever the zoom
    assert np.array_equal(l1, ls) and np.array_equal(p1, ps)
    # the raw widths, the reference's formula from each edge's depth: the
    # drawn width is ≥ 1 px, the sub-pixel part folded into the alpha
    s = _view()
    assert not is_3d(s.shape)
    g = geom(s.shape)
    _, _, pd = world_points(g["V"], view_angles(s.shape, s.ang), s.yaw, s.pitch, d4=s.depth4)
    near, span = pd.min(), max(pd.max() - pd.min(), 1e-6)
    E = g["E"]
    t = np.sort((pd[E[:, 0]] + pd[E[:, 1]]) * 0.5 - near) / span
    assert g["m"] <= 500                             # not heavy
    raw = (0.5 + 1.5 * t) * min(0.75 + 0.35 * 1.6, 1.35)
    np.testing.assert_allclose(l1[0::6, 8], np.maximum(raw, 1.0), rtol=1e-5)
    np.testing.assert_allclose(lw[0::6, 8], np.maximum(raw * zoom, 1.0), rtol=1e-5)
    np.testing.assert_allclose(lw[0::6, 9] * np.minimum(raw, 1.0),
                               l1[0::6, 9] * np.minimum(raw * zoom, 1.0), rtol=1e-5)
    if zoom < 1:
        assert (lw[:, 8] <= l1[:, 8]).all() and (lw[:, 9] < l1[:, 9]).any()
    else:
        assert (lw[:, 8] > l1[:, 8]).all()
    # the radii: the pre-A2 formula × zoom, then rounded to whole pixels
    tp = np.sort((pd - near) / span)
    r_raw = 1.7 + 2.3 * tp * tp                      # not heavy; dpr 1
    np.testing.assert_allclose(p1[0::6, 5], np.floor(2 * r_raw + 0.5) / 2, rtol=1e-6)
    np.testing.assert_allclose(pw[0::6, 5], np.floor(2 * r_raw * zoom + 0.5) / 2, rtol=1e-6)
    if zoom < 1:
        assert (pw[:, 5] < p1[:, 5]).all()            # every dot smaller
    else:
        assert (pw[:, 5] > p1[:, 5]).all()            # every dot bigger


@pytest.mark.parametrize("zoom", [0.5, 2.0])
def test_on_the_fitted_field_the_shaders_scale_the_strokes(ctx, monkeypatch, zoom):  # noqa: F811
    """On field.py's path (Fit, a 3D lattice) each copy has its own scale,
    the camera's zoom in it: the rows carry the reference's width and
    radius at scale 1 whatever the zoom, and LINE_VS / POINT_VS scale them
    by the copy in world space only — heavier above scale 1, lighter below."""
    l1 = _strokes(ctx, monkeypatch, zoom=1.0, bright=1.6, inst_fit=True)
    lw = _strokes(ctx, monkeypatch, zoom=zoom, bright=1.6, inst_fit=True)
    ls = _strokes(ctx, monkeypatch, zoom=zoom, bright=1.6, inst_fit=True, screen_strokes=True)
    for got in (lw, ls):
        assert np.array_equal(l1["lines"], got["lines"])
        assert np.array_equal(l1["points"], got["points"])
    assert lw["wscale"] == (1.0, 1.0) and ls["wscale"] == (0.0, 0.0)
    assert np.array_equal(lw["model"], np.eye(4, dtype=np.float32))
    world, _ = _draw(ctx, _view(lines=True, zoom=zoom, bright=1.6, inst_fit=True))
    screen, _ = _draw(ctx, _view(lines=True, zoom=zoom, bright=1.6, inst_fit=True,
                                 screen_strokes=True))
    # Fit frames the copy (its scale is never under the framed size, as a
    # zoom under 1 does not shrink a fitted field): heavier past scale 1
    k = float(lw["copies"][0, 2])
    assert k != 1.0
    ink_w, ink_s = world[..., :3].sum(), screen[..., :3].sum()
    assert (ink_w > ink_s) if k > 1 else (ink_w < ink_s), (k, ink_w, ink_s)
