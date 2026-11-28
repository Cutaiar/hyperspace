"""What the pane's switcher and the footer keep: each kept answer is the
fresh one, and goes when what it was made of does."""

from __future__ import annotations

from types import SimpleNamespace as NS

import pytest
from imgui_bundle import imgui

from hyperspace import ui, ui_pane, ui_switcher
from hyperspace.dkit import draw, menu
from hyperspace.dkit.ease import Anim
from hyperspace.graph import BUS_PORTS, EMPTY, BusCuts, Wire, Wiring, bus_wire
from hyperspace.library import Install
from hyperspace.params import Kind, Param, Registry

RED, GREY = (1.0, 0.1, 0.1, 1.0), (0.5, 0.5, 0.5, 0.75)


def _param(pid: str, group: str, box: dict) -> Param:
    box.setdefault(pid, 0.5)
    return Param(id=pid, label=pid, kind=Kind.CONTINUOUS, get=lambda: box[pid],
                 put=lambda v: box.__setitem__(pid, v), lo=0.0, hi=1.0, group=group)


@pytest.fixture
def dl():
    """The draw list of a window, in an imgui frame."""
    ctx = imgui.create_context()
    io = imgui.get_io()
    io.display_size = imgui.ImVec2(400, 300)
    io.backend_flags |= imgui.BackendFlags_.renderer_has_textures
    imgui.new_frame()
    imgui.begin("w")
    yield imgui.get_window_draw_list()
    imgui.end()
    imgui.end_frame()
    imgui.destroy_context(ctx)


def _strokes(dl, name, *a, **k):
    """The vertices and indices (the list's own offset off) an icon adds to `dl`."""
    v0, i0 = dl.vtx_buffer.size(), dl.idx_buffer.size()
    draw.icon(dl, name, *a, **k)
    return ([(v.pos.x, v.pos.y, v.uv.x, v.uv.y, v.col)
             for v in (dl.vtx_buffer[n] for n in range(v0, dl.vtx_buffer.size()))],
            [dl.idx_buffer[n] - v0 for n in range(i0, dl.idx_buffer.size())])


def test_a_kept_icon_is_the_icon_drawn_afresh_wherever_it_goes(dl):
    kept: dict = {}
    for name in draw.ICONS:
        for x, y, size, col in ((10.5, 20.25, 16.0, RED), (10.5, 20.25, 16.0, GREY),
                                (11.0, 20.25, 16.0, GREY), (11.0, 33.3, 16.0, GREY),
                                (11.0, 33.3, 12.0, GREY)):
            fresh = _strokes(dl, name, x, y, size, col)
            assert fresh[0]
            assert _strokes(dl, name, x, y, size, col, kept=kept, slot="a") == fresh
            assert _strokes(dl, name, x, y, size, col, kept=kept, slot="a") == fresh
    assert list(kept) == ["a"]                        # a slot holds its last, not a history


def test_a_kept_icon_follows_its_geometry_its_width_and_the_tessellation(dl, monkeypatch):
    kept: dict = {}

    def same(**k):
        assert (_strokes(dl, "cpu", 3, 4, 16, RED, kept=kept, slot="a", **k)
                == _strokes(dl, "cpu", 3, 4, 16, RED, **k))
    same()
    same(width=3.0)
    monkeypatch.setitem(draw.ICONS, "cpu", [[("M", 2, 2), ("L", 20, 20)]])     # a hot reload
    same()
    was = kept["a"]
    imgui.get_style().curve_tessellation_tol = 5.0
    same()
    assert kept["a"] is not was


def test_a_closed_menu_sizes_nothing_and_leaves_no_rect(dl, monkeypatch):
    kit = NS(anim=Anim())
    monkeypatch.setitem(menu.LAST_RECT, "##m", (1, 2, 3, 4))
    monkeypatch.setattr(menu, "measure", lambda *a, **k: pytest.fail("a closed menu was measured"))
    kit.anim.to("##m:open", 1.0)
    assert menu.popup(kit, "##m", [menu.Item(id="a", label="a")]) is None
    assert "##m" not in menu.LAST_RECT
    assert kit.anim._t["##m:open"].target == 0.0


def test_the_switchers_rows_follow_the_view_and_the_tables(monkeypatch):
    monkeypatch.setattr(ui_switcher, "_KEPT", {})

    def rows(key):
        return ui_switcher._plain_items(menu, ui_switcher._by_key()[0], key)

    def fresh(key):
        titles = {k: t for k, t, _, _ in ui_pane.SECTIONS}
        return [menu.Item(id=k, label=titles[k], checked=k == key) for k in ui_pane.MENU]

    for key in ("fx", "fx", "camera", "audio", "fx"):
        assert rows(key) == fresh(key)
    assert rows("fx") is rows("fx")
    monkeypatch.setattr(ui_pane, "SECTIONS", tuple(               # a reload of ui_pane
        (k, t.upper(), ("view",), b) for k, t, _, b in ui_pane.SECTIONS))
    titles, groups = ui_switcher._by_key()
    assert titles["fx"] == "FX" and groups["fx"] == ("view",) and rows("fx") == fresh("fx")
    monkeypatch.setattr(ui_pane, "MENU", ui_pane.MENU[1:])
    assert rows("fx") == fresh("fx")
    old = menu.Item
    monkeypatch.setattr(menu, "Item", type("Item", (old,), {}))   # a reload of the kit's menu
    assert type(rows("fx")[0]) is menu.Item is not old


def test_the_held_back_ids_follow_the_registry_and_the_session():
    reg, box = Registry(), {}
    reg.add(_param("output.y", "output", box))
    show = Install.__new__(Install)
    show.lib = NS(reg=reg, _need_reg=lambda: reg)
    show.session = {"ghost.3.alpha": 0.25, "output.y": 0.5, "output.gone": 1, "ghost.2.alpha": 0.5}
    assert list(show._held_back().items()) == [("ghost.3.alpha", 0.25), ("ghost.2.alpha", 0.5)]
    reg.add(_param("ghost.2.alpha", "ghost", box))
    assert show._held_back() == {"ghost.3.alpha": 0.25}
    reg.remove("ghost.2.alpha")
    show.session["ghost.2.alpha"] = 0.75              # the same session, changed in place
    assert show._held_back() == {"ghost.2.alpha": 0.75, "ghost.3.alpha": 0.25}
    show.session = {"output.y": 0.5}                  # a load's
    assert show._held_back() == {}
    show.session, show.lib.reg = {"ghost.2.alpha": 0.5, "output.y": 1}, None
    assert show._held_back() == {"ghost.2.alpha": 0.5}
    show.session, show.lib.reg = None, reg
    assert show._held_back() == {}


def test_the_footers_dot_follows_an_edit_an_undo_a_save_and_a_load(tmp_path):
    from test_ui_shell import build_rig
    with build_rig(tmp_path) as r:
        lib, p = r.panel.library, r.panel.reg["output.alpha"]
        lib.install.save("a")
        assert not lib.install.is_dirty()
        was = p.base
        p.set_value(0.4)
        assert lib.install.is_dirty()                 # the next ask, not a poll later
        p.set_value(was)                              # (what an undo writes)
        assert not lib.install.is_dirty()
        p.set_value(0.4)
        lib.install.save("b")
        assert not lib.install.is_dirty()
        lib.install.load("a")
        assert p.base == was and not lib.install.is_dirty()


def test_why_an_output_is_black_follows_everything_it_is_made_of(monkeypatch):
    wired = Wiring(wires=(Wire("scene", "output.all.image"),), wired=True)
    sw, other = (NS(scene=True, hands=True, dim=1.0) for _ in range(2))
    st = NS(fx=False, hand=False, master=1.0, wiring=wired, cuts=BusCuts())
    p = object.__new__(ui.Panel)
    p.outputs = [NS(n=1, opened=True, switches=sw), NS(n=2, opened=True, switches=other)]
    p._outputs_now = lambda: (st.fx, st.hand, st.master)
    p.graph_now = lambda: (st.wiring, None)
    p.bus_cuts_now = lambda: st.cuts
    real, asked = ui.output_shows, []

    def counted(*a, **k):
        asked.append(k["n"])
        return real(*a, **k)

    def black():
        """`black_outputs`, which is the fresh answer, asked twice."""
        fresh = [s.n for s in p.outputs
                 if real(s.switches, st.fx, st.hand, st.master, st.wiring, n=s.n,
                         bus_cuts=st.cuts)[1] not in ("", "master")]
        assert p.black_outputs() == fresh == p.black_outputs()
        return fresh

    monkeypatch.setattr(ui, "output_shows", counted)
    assert black() == [] and asked == [1, 2]          # kept the second time
    sw.dim = 0.0
    assert black() == [1] and asked == [1, 2, 1]      # that window's alone
    sw.dim, other.scene = 1.0, False
    assert black() == [2]
    other.scene = True
    st.master = 0.0
    assert black() == []                              # the footer's own "dim black"
    st.master, st.cuts = 1.0, BusCuts(frozenset({bus_wire(2, BUS_PORTS[0])}))
    assert black() == [2]
    st.cuts, st.wiring = BusCuts(), EMPTY             # another patch
    assert black() == [1, 2]
    st.wiring = Wiring(wires=(Wire("hands.layer", "output.all.hands"),), wired=True)
    assert black() == [1, 2]
    st.hand = True
    assert black() == []
    sw.hands = False
    assert black() == [1]
    st.fx = True
    black()
    monkeypatch.setattr(ui, "output_shows", lambda *a, **k: ("", "reloaded"))   # a hot reload
    assert p.black_outputs() == [1, 2]
