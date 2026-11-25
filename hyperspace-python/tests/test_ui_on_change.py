"""What the panel works out once and keeps (2026-11-25): each memo holds what a
fresh answer would be, and goes when what it was made of does."""

from __future__ import annotations

from types import SimpleNamespace as NS

import pytest

from hyperspace import graphview
from hyperspace.graphview import VCable, View, VNode, VPort
from hyperspace.params import Kind, Param, Registry, part_of


def _param(pid: str, group: str, box: dict) -> Param:
    box.setdefault(pid, 0.5)
    return Param(id=pid, label=pid, kind=Kind.CONTINUOUS, get=lambda: box[pid],
                 put=lambda v: box.__setitem__(pid, v), lo=0.0, hi=1.0, group=group)


def test_a_group_and_a_part_follow_an_add_and_a_remove():
    reg, box = Registry(), {}
    reg.add(_param("fx.a.x", "fx", box))
    reg.add(_param("output.y", "output", box))
    assert [p.id for p in reg.group("fx")] == ["fx.a.x"]
    for part in ("patch", "shared_meta"):
        assert set(reg.snapshot(part=part)) == {p.id for p in reg if part_of(p) == part}
    reg.add(_param("fx.b.x", "fx", box))
    assert [p.id for p in reg.group("fx")] == ["fx.a.x", "fx.b.x"]
    assert "fx.b.x" in reg.snapshot(part="patch")
    reg.remove("fx.a.x")
    assert [p.id for p in reg.group("fx")] == ["fx.b.x"]
    assert "fx.a.x" not in reg.snapshot(part="patch")
    again = reg.add(_param("fx.a.x", "fx", {}))       # removed and declared again: the new one
    assert reg.group("fx")[-1] is again
    reg.group("fx").clear()                           # the caller's own list
    assert len(reg.group("fx")) == 2


def test_a_snapshot_reads_the_bases_as_they_are_now():
    reg, box = Registry(), {}
    reg.add(_param("fx.a.x", "fx", box))
    assert reg.snapshot(part="patch")["fx.a.x"] == 0.5
    box["fx.a.x"] = 0.25                              # past the registry: the object's own value
    assert reg.snapshot(part="patch")["fx.a.x"] == 0.25


def _view() -> View:
    a = VNode("device:pad", "device", "pad", ports=[VPort("o", "o", graphview.OUT)])
    b = VNode("group:view", "group", "view", ports=[VPort("i", "i", graphview.IN)])
    return View([a, b], [VCable("c", "pa", "pb", addr="pad:x")],
                pins={"pa": ("device:pad", "o"), "pb": ("group:view", "i")})


def test_a_views_memos_are_its_own_and_follow_its_structure():
    v = _view()
    assert v.source_owners() == [v.owner("pa")] and v.source_owners() is v.source_owners()
    assert graphview.patch_only(v) == {"device:pad", "group:view"}       # no section: all of it
    v.nodes.append(VNode("lfo:1", "lfo", "LFO 1"))
    assert "lfo:1" in graphview.patch_only(v)
    v.cables.append(VCable("d", "pb", "pa"))
    assert len(v.source_owners()) == 2


def test_an_address_is_read_once_a_refresh_and_afresh_the_next():
    v = _view()
    v.cables.append(VCable("c2", "pa", "pb", addr="pad:x"))
    asked, vec = [], [0.25]

    def lane(addr):
        asked.append(addr)
        return "pad", 0

    r = NS(feeds={"pad": vec}, modgraph_cut=(), lane=lane)
    graphview.refresh(v, {}, r)
    assert [c.live for c in v.cables] == [0.25, 0.25] and asked == ["pad:x"]
    vec[0] = 0.75
    graphview.refresh(v, {}, r)
    assert [c.live for c in v.cables] == [0.75, 0.75]
    r.feeds = {}                                      # let go: not live, the cables dormant
    graphview.refresh(v, {}, r)
    assert all(c.live is None and c.dormant for c in v.cables)


def test_a_lost_device_still_greys_its_cables():
    v = _view()
    r = NS(feeds={"pad": [0.5]}, modgraph_cut=(), lane=lambda a: ("pad", 0))
    graphview.refresh(v, {}, r)
    assert not v.cables[0].dormant
    v.nodes[0].grey = True
    graphview.refresh(v, {}, r)
    assert v.cables[0].dormant


@pytest.mark.parametrize("native", [True, False])
def test_the_renderer_draws_in_cpp_or_as_it_did(monkeypatch, native):
    from hyperspace import imgui_gl

    said = []
    monkeypatch.setattr(imgui_gl.imgui, "backends", NS(
        opengl3_new_frame=lambda: said.append("new"),
        opengl3_render_draw_data=lambda d: said.append("draw")))
    monkeypatch.setattr(imgui_gl.GlfwRenderer, "render", lambda self, d: said.append("python"))
    r = object.__new__(imgui_gl.ControlRenderer)
    r.native, r.io = native, NS(display_framebuffer_scale=(2.0, 2.0))
    r._update_textures = lambda: said.append("textures")
    r.render(NS(scale_clip_rects=lambda k: said.append(k)))
    # the clip rects are left in framebuffer pixels, after the draw: `replay.grab` reads them so
    assert said == (["textures", "new", "draw", (2.0, 2.0)] if native else ["python"])
