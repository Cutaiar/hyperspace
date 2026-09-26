"""Routing matrix — the lanes → params half of the binding table (WP5b).

The ROUTING page. Rows are the router's `mod` / `replace` routes from
`lane:i` (and `ext:i` / `hand:i` when the bridge / hands feed them), two lines each:

  [on] source        target ▾            op ▾           ×
       depth ────────────  × scale ▾   ▮▮▮▯▯│ live

The target is a searchable combo over every modulatable param, grouped
by registry group; depth is signed — ±1 for `mod` (norm units: 1 puts a
lane at the asymptote on the param's end stop), the target's own range
for `replace`; scale names an attenuator param or none. The live bar is
the source's normalized reading (white) with a red hairline at the
target's effective norm, so a route can be read working. Edits land on
the table at once (the router reads it every frame) — nothing here is
copied.

The strip under the title is the preset strip's look over routing
preset *files* (routing.preset_files): prev / next / the list load
through `Router.load_preset`, save / as… write through
`Router.save_preset` into the user library's bindings/ folder, reset is
the factory default. The library's own strip can't do this — bindings/
is a folder without a registry group, so `is_dirty` has nothing to
compare — hence the dirty dot here is the routes against a snapshot
taken at the last load or save.

The panel reaches the router through `panel.router`, which app.py is
meant to set; until it does, the table is found through the MIDI
adapter (it shares it) and a Router is made over it — everything works
but the bridge's `ext` feeds, which that router never sees. Right-click
on any widget elsewhere offers "Route a lane here…" (`ctx_item`): a
`lane:<selected band>` → that param `mod` route at depth 0.5, and the
page opens on it.
"""

from __future__ import annotations

import math

from imgui_bundle import imgui

from . import ui, ui_presets
from .bands import CEIL
from .params import Kind, Param
from .routing import FACTORY_DIR, Binding, Router, preset_files

KEY = "bindings"          # the name-field / listing key on the panel's preset state
DEPTH_MOD = 1.0           # ±, the `mod` depth slider's throw
N_EXT = 16                # ext lanes offered once any ext source is around
BAR_W = 56.0


# ---- state on the panel ----

def _state(panel) -> dict:
    st = getattr(panel, "_routing_state", None)
    if st is None:
        st = panel._routing_state = {"current": None, "snap": None, "error": "",
                                     "names": None, "filter": ""}
    return st


def router_of(panel) -> Router | None:
    """The app's router, or one over the MIDI adapter's (shared) table."""
    r = getattr(panel, "router", None)
    if r is None and panel.midi is not None:
        r = panel.router = Router(panel.reg, panel.midi.map.table)
    return r


def _home(panel):
    lib = panel.library
    return lib.home if lib is not None else None


def _snapshot(router: Router) -> list[dict]:
    return [b.to_json() for b in router.table.routes()]


def dirty(panel, router: Router) -> bool:
    st = _state(panel)
    return st["snap"] is not None and _snapshot(router) != st["snap"]


def files(panel) -> dict:
    """name → path of the routing preset files, re-listed on the strip's
    poll cadence (a glob per frame would be wasteful, never wrong)."""
    st, now = _state(panel), imgui.get_time()
    hit = st["names"]
    if hit is None or now - hit[0] >= ui_presets.LIST_POLL:
        st["names"] = hit = (now, preset_files(_home(panel)))
    return hit[1]


def names(panel) -> list[str]:
    return sorted(files(panel), key=str.lower)


def _factory(panel, name: str | None) -> bool:
    p = files(panel).get(name)
    return p is not None and FACTORY_DIR in p.parents


def invalidate(panel) -> None:
    _state(panel)["names"] = None


# ---- preset actions (what the strip's buttons do; tests call these) ----

def load(panel, router: Router, name: str) -> None:
    st = _state(panel)
    try:
        missing = router.load_preset(name, _home(panel))
    except (OSError, ValueError, KeyError) as e:
        st["error"] = f"routing: {e}"
        return
    st["current"], st["snap"], st["error"] = name, _snapshot(router), ""
    if missing and panel.library is not None:
        panel.library.report(missing, f"routing preset {name}")


def step(panel, router: Router, n: int) -> str | None:
    """prev / next by name order; from nothing, the first or the last."""
    listing = names(panel)
    if not listing:
        return None
    cur = _state(panel)["current"]
    k = listing.index(cur) if cur in listing else (-1 if n > 0 else 0)
    name = listing[(k + n) % len(listing)]
    load(panel, router, name)
    return name


def save_as(panel, router: Router, name: str) -> None:
    st, home = _state(panel), _home(panel)
    if home is None:
        st["error"] = "routing: no library to save into"
        return
    try:
        path = router.save_preset(name, home)
    except OSError as e:
        st["error"] = f"routing: {e}"
        return
    st["current"], st["snap"], st["error"] = path.name[:-5], _snapshot(router), ""
    invalidate(panel)


def add_route(panel, target: str, source: str | None = None, depth: float = 0.5) -> Binding:
    """A new `mod` row from the selected band's lane (or `source`) to target."""
    router = router_of(panel)
    src = source or f"lane:{panel.control.selb}"
    return router.table.add(Binding(src, target, "mod", depth))


def ctx_item(panel, p: Param) -> None:
    """The context menu's line: route the selected band's lane to this param."""
    real = panel._real(p)
    if router_of(panel) is None:
        return
    if not real.modulatable:
        imgui.text_disabled("not modulatable")
        return
    if imgui.menu_item_simple("Route a lane here…"):
        add_route(panel, real.id)
        panel.reg["ui.page"].set(ui.PAGE_KEYS.index("routing"))


# ---- the strip ----

def strip(panel, router: Router) -> None:
    """◀ name ● ▶ · save · as… · reset — over the routing preset files."""
    st = _state(panel)
    imgui.push_id("strip.routing")
    if ui_presets._name_field(panel, KEY, lambda n: save_as(panel, router, n)):
        imgui.pop_id()
        return
    cur = st["current"]
    listing = names(panel)
    factory = _factory(panel, cur)
    is_dirty = dirty(panel, router)
    imgui.begin_disabled(not listing)
    if imgui.arrow_button("prev", imgui.Dir.left):
        step(panel, router, -1)
    imgui.same_line(0, 2)
    label = ui_presets._elide(cur) if cur else "—"
    imgui.push_style_color(imgui.Col_.button, imgui.ImVec4(0, 0, 0, 0))
    imgui.push_style_color(imgui.Col_.text, ui.DIM if factory or cur is None else
                           imgui.ImVec4(0.92, 0.92, 0.92, 1))
    if imgui.button(f"{label}##name", imgui.ImVec2(ui_presets.NAME_MAX * 7.4 + 8, 0)):
        imgui.open_popup("list")
    imgui.pop_style_color(2)
    if imgui.is_item_hovered():
        imgui.set_tooltip(f"{cur}  ·  {'factory' if factory else 'user'} routing preset — "
                          "click for the list" if cur else
                          "the routes as loaded from the project's bindings.json")
    if is_dirty:
        imgui.same_line(0, 0)
        imgui.text_colored(ui.RED, "●")
        if imgui.is_item_hovered():
            imgui.set_tooltip("routes edited since the preset loaded")
    imgui.same_line(0, 2)
    if imgui.arrow_button("next", imgui.Dir.right):
        step(panel, router, 1)
    imgui.end_disabled()
    if imgui.begin_popup("list"):
        ui._micro("routing")
        for name in listing:
            fac = _factory(panel, name)
            imgui.push_style_color(imgui.Col_.text, ui.DIM if fac else
                                   imgui.ImVec4(0.92, 0.92, 0.92, 1))
            picked, _ = imgui.selectable(f"{name}##pick", name == cur)
            imgui.pop_style_color()
            if picked:
                load(panel, router, name)
        imgui.end_popup()
    imgui.same_line(imgui.get_content_region_avail().x - 128)
    imgui.begin_disabled(cur is None or factory or _home(panel) is None)
    if imgui.small_button("save"):
        save_as(panel, router, cur)
    imgui.end_disabled()
    if imgui.is_item_hovered(imgui.HoveredFlags_.allow_when_disabled):
        imgui.set_tooltip("Write the routes over the current preset"
                          + (" — a factory preset: save as… instead" if factory else ""))
    imgui.same_line()
    if imgui.small_button("as…"):
        ui_presets._begin_naming(panel, KEY, cur or "")
    if imgui.is_item_hovered():
        imgui.set_tooltip("Save the routes as a new user preset (library/bindings/)")
    imgui.same_line()
    if imgui.small_button("reset"):
        load(panel, router, "default")
    if imgui.is_item_hovered():
        imgui.set_tooltip("Back to the factory routes — legacy 6 on the pattern base of 1")
    imgui.pop_id()


# ---- the rows ----

def _sources(panel, router: Router) -> list[tuple[str, str]]:
    """(source, label) the combo offers: every lane as "i NAME", and the
    ext lanes once the bridge feeds them or a row names one."""
    chain = panel.audio.chain
    out = [(f"lane:{i}", f"{i} {name}") for i, name in enumerate(chain.band_names)]
    ext = router.feeds.get("ext") is not None or any(
        b.scheme == "ext" for b in router.table.bindings)
    if ext:
        out += [(f"ext:{i}", f"ext {i}") for i in range(N_EXT)]
    names = getattr(router, "labels", {}).get("hand") or []
    if router.feeds.get("hand") is not None or names:
        out += [(f"hand:{i}", f"hand {n}") for i, n in enumerate(names)]
    return out


def _live(panel, router: Router, b: Binding) -> float | None:
    """The source's normalized reading this frame, None while it isn't live."""
    i = b.index
    if b.scheme == "lane":
        a = panel.audio
        if not getattr(a, "on", False) or not 0 <= i < a.chain.n:
            return None
        return float(a.chain.lanes[i]) / CEIL
    vec = router.feeds.get(b.scheme)
    if vec is None or not 0 <= i < len(vec):
        return None
    u = float(vec[i])
    return None if math.isnan(u) else u     # NaN: a hand out of view


def _targets(panel) -> list[Param]:
    return [p for p in panel.reg if p.modulatable and not p.alias]


def _param_combo(panel, label: str, current: str | None, width: float,
                 candidates: list[Param], none: str | None = None) -> str | None | bool:
    """A searchable combo over params, grouped: returns the id picked, None
    for the `none` entry, or False when nothing changed."""
    st = _state(panel)
    imgui.set_next_item_width(width)
    shown = current if current is not None else (none or "—")
    if not imgui.begin_combo(label, shown):
        return False
    picked: str | None | bool = False
    if imgui.is_window_appearing():
        st["filter"] = ""
        imgui.set_keyboard_focus_here()
    imgui.set_next_item_width(-1)
    _, st["filter"] = imgui.input_text_with_hint("##find", "find", st["filter"])
    needle = st["filter"].lower()
    if none is not None:
        sel, _ = imgui.selectable(none, current is None)
        if sel:
            picked = None
    group = None
    for p in candidates:
        if needle and needle not in p.id.lower() and needle not in p.label.lower():
            continue
        if p.group != group:
            group = p.group
            ui._micro(group or "misc")
        sel, _ = imgui.selectable(f"{p.id}##{p.id}", p.id == current)
        if imgui.is_item_hovered() and p.tip:
            imgui.set_tooltip(p.tip)
        if sel:
            picked = p.id
    imgui.end_combo()
    return picked


def _row(panel, router: Router, b: Binding, k: int) -> bool:
    """One route, two lines; returns True when the row asked to be deleted."""
    reg = panel.reg
    imgui.push_id(k)
    p = reg.get(b.target)
    # line 1: on · source · target · op · ×
    changed, on = imgui.checkbox("##on", b.enabled)
    if changed:
        b.enabled = on
    if imgui.is_item_hovered():
        imgui.set_tooltip("Enabled — a dormant row keeps its settings")
    imgui.same_line()
    sources = _sources(panel, router)
    labels = [lb for _, lb in sources]
    cur = next((i for i, (s, _) in enumerate(sources) if s == b.source), -1)
    imgui.set_next_item_width(76)
    if cur < 0:
        labels, cur = labels + [b.source], len(labels)
    changed, i = imgui.combo("##src", cur, labels)
    if changed and i < len(sources):
        b.source = sources[i][0]
    imgui.same_line()
    picked = _param_combo(panel, "##target", b.target, 130, _targets(panel))
    if picked:
        b.target = picked
    if p is None:
        if imgui.is_item_hovered():
            imgui.set_tooltip(f"{b.target}: no such param — the row is dormant")
    elif not p.modulatable and imgui.is_item_hovered():
        imgui.set_tooltip(f"{b.target} is not modulatable — the row is dormant")
    imgui.same_line()
    imgui.set_next_item_width(48)
    changed, op = imgui.combo("##op", 1 if b.op == "replace" else 0, ["mod", "repl"])
    if changed:
        b.op = "replace" if op else "mod"
    if imgui.is_item_hovered():
        imgui.set_tooltip("mod: depth × source added to the base\n"
                          "repl: depth × source is the value while the source is live")
    imgui.same_line(imgui.get_content_region_avail().x - 14)
    imgui.push_style_color(imgui.Col_.text, ui.DIM)
    kill = imgui.small_button("×")
    imgui.pop_style_color()
    if imgui.is_item_hovered():
        imgui.set_tooltip("Delete this route")
    # line 2: depth · scale · live
    imgui.dummy(imgui.ImVec2(18, 0))
    imgui.same_line()
    imgui.set_next_item_width(112)
    if b.op == "replace" and p is not None and p.kind is Kind.CONTINUOUS:
        lo, hi, fmt = float(p.lo), float(p.hi), "%.3g"
    else:
        lo, hi, fmt = -DEPTH_MOD, DEPTH_MOD, "%+.2f"
    changed, v = imgui.slider_float("##depth", float(b.value), lo, hi, fmt)
    if changed:
        b.value = v
    if imgui.is_item_hovered():
        imgui.set_tooltip("Depth, signed" + (" — in the target's own units" if b.op == "replace"
                                             else " — 1 is the full throw at a lane's asymptote")
                          + "\nctrl-click to type")
    imgui.same_line()
    scale = _param_combo(panel, "##scale", b.scale, 100,
                         [q for q in reg if q.kind is Kind.CONTINUOUS and not q.alias],
                         none="× 1")
    if scale is not False:
        b.scale = scale
    if imgui.is_item_hovered():
        imgui.set_tooltip("A param whose live value multiplies the depth (master.gain "
                          "on the rate routes)")
    imgui.same_line()
    _live_bar(panel, router, b, p)
    imgui.pop_id()
    return kill


def _live_bar(panel, router: Router, b: Binding, p: Param | None) -> None:
    """Source reading (white fill) and target effective norm (red hairline)."""
    u = _live(panel, router, b) if b.enabled else None
    h = imgui.get_frame_height()
    pos = imgui.get_cursor_screen_pos()
    dl = imgui.get_window_draw_list()
    u32 = imgui.color_convert_float4_to_u32
    x0, y0, x1, y1 = pos.x, pos.y + 3, pos.x + BAR_W, pos.y + h - 3
    dl.add_rect(imgui.ImVec2(x0, y0), imgui.ImVec2(x1, y1),
                u32(imgui.ImVec4(0.25, 0.25, 0.25, 1)))
    if u is not None:
        w = (x1 - x0 - 2) * min(max(u, 0.0), 1.0)
        dl.add_rect_filled(imgui.ImVec2(x0 + 1, y0 + 1), imgui.ImVec2(x0 + 1 + w, y1 - 1),
                           u32(imgui.ImVec4(0.92, 0.92, 0.92, 0.85)))
    if p is not None and p.modulated:
        x = x0 + 1 + (x1 - x0 - 2) * p.eff_norm
        dl.add_line(imgui.ImVec2(x, y0), imgui.ImVec2(x, y1), u32(ui.RED), 1.0)
        panel.ghosts += 1
    imgui.dummy(imgui.ImVec2(BAR_W, h))
    if imgui.is_item_hovered():
        src = "not live" if u is None else f"{u:.2f}"
        tgt = "—" if p is None else (f"{p.text()} → {panel._eff_text(p)}" if p.modulated
                                     else p.text())
        imgui.set_tooltip(f"source {src}  ·  target {tgt}")


# ---- the page ----

def page(panel, dt: float) -> None:
    st = _state(panel)
    router = router_of(panel)
    ui._micro("routing")
    if router is None:
        imgui.separator()
        imgui.text_disabled("no router attached")
        return
    strip(panel, router)
    imgui.separator()
    rows = router.table.routes()
    chain = panel.audio.chain
    live = "live" if getattr(panel.audio, "on", False) else "no source — lanes idle"
    imgui.text_disabled(f"{len(rows)} routes  ·  {chain.n} lanes  ·  {live}")
    imgui.same_line(imgui.get_content_region_avail().x - 60)
    if imgui.small_button("+ route"):
        pid = f"pattern.mod.{panel.control.selb}"
        add_route(panel, pid if pid in panel.reg else _targets(panel)[0].id)
    if imgui.is_item_hovered():
        imgui.set_tooltip("A new route from the selected band's lane — or right-click "
                          "any control: Route a lane here…")
    if st["error"]:
        imgui.text_colored(ui.WARN, st["error"])
    # the rows scroll if they must; the strip and the header stay put
    if imgui.begin_child("##routes", imgui.ImVec2(0, 0)):
        dead = None
        for k, b in enumerate(rows):
            if _row(panel, router, b, k):
                dead = b
            imgui.separator()
        if dead is not None:
            router.table.remove(dead)
        if not rows:
            imgui.text_disabled("no routes — the lanes drive nothing")
    imgui.end_child()
