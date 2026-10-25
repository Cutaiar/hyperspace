"""Plan 35 T4: the retired switch states as wiring, for the tests.

The pipelines are gone: a frame is its wires (`graph.build_graph`), and
what an output's three switches used to give it — the scene, the hands
over, the hands through the effects — is that output's own wires over All
outputs' (`graphmigrate.output_wires`, `Shows`). The golden tool draws its
states so (`tools/golden_frames.py`, `rig_section`), and the frame
signatures prove it node for node against the retired `default_graph`
(`tests/fixtures/frame-signatures.json`). These helpers say a test's
switch states the same way: every window's mutes on, each state its
output's wiring.

    graph([Shows(), Shows(through=True)], src, effects=("acid",))
    r.wiring = wiring(r.wiring, Shows(), Shows(scene=False, through=True))
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hyperspace import graph as G
from hyperspace import graphmigrate as M
from hyperspace.outputs import Switches, View

Shows = M.Shows


def section(src: Any = None, **kw) -> dict:
    """`src` as a wired frame's section: a `Wiring` (unwired: as a load
    wires it, `graphmigrate.wired_of`; None, the factory look), a section
    dict or `GraphSpec` before the wired frame (renamed and wired, as the
    load's migration does), or a wired one as it is."""
    if src is None:
        src = G.Wiring()
    if isinstance(src, G.Wiring):
        if src.wired:
            raise TypeError("a wired Wiring has no section: pass the section")
        return M.wired_of(src)
    if isinstance(src, G.GraphSpec):
        src = src.to_json()
    if src.get(G.FRAME_KEY) == G.WIRED_FRAME:
        return src
    if not M.has_frame_run(G.read_graph(src)):
        # (a section from before plan 33's run: the load's migration, which
        # writes each wire D1 would write short as the entry it stood for)
        values = {"backdrop.history": True} if kw.get("backdrop_history") else {}
        doc, _ = M.migrate({"values": values, "graph": src}, {})
        return doc["graph"]
    return M.wired_section(M.renamed(src), G.read_graph(src), **kw)


def shown(src: Any = None, *shows: Shows, **kw) -> dict:
    """`section(src)` with output k's overrides for `shows[k - 1]`."""
    sec = section(src, **kw)
    for k, sh in enumerate(shows):
        if sh != Shows():
            sec = M.with_output_wires(sec, k + 1, sh)
    return sec


def wiring(src: Any = None, *shows: Shows, **kw) -> G.Wiring:
    """The wired `Wiring` of `shown(src, *shows)` — what a renderer is
    handed (`Renderer.wiring`); every window's mutes on."""
    got = G.read_graph(shown(src, *shows, **kw))
    assert not got.notes, got.notes
    return got.wiring()


@dataclass
class Thru:
    """A window whose state is wired (the retired `Switches(through=True)`,
    and any other `Shows` with the window's own look): its picture, its
    hands, through the effects or not — written into the renderer's wiring
    (`wire_switches`) — and the window's dim and mirror, every mute on."""

    scene: bool = True
    hands: bool = True
    through: bool = True
    dim: float = 1.0
    flip_x: bool = False
    flip_y: bool = False

    @property
    def shows(self) -> Shows:
        return Shows(self.scene, self.hands, self.through)


def wire_switches(r, *states) -> list[Switches]:
    """Renderer `r` wired for `states` — each a `Thru` or a `Switches`
    (the retired switches' scene and hands), its output's wiring, as the
    golden rig draws its states — over its own unwired wiring (kept on `r`
    the first time, so a second call wires the same base); the windows'
    `Switches`: their dim and mirror, every mute on."""
    base = getattr(r, "_wiredframe_base", None)
    if base is None or getattr(r.wiring, "wired", False) is False:
        base = r._wiredframe_base = r.wiring
    shows = [s.shows if isinstance(s, Thru) else Shows(s.scene, s.hands) for s in states]
    r.wiring = wiring(base, *shows)
    return [Switches(dim=s.dim, flip_x=s.flip_x, flip_y=s.flip_y) for s in states]


def views(shows, size=(10, 10)) -> list[View]:
    """One window per state, every mute on (the state is its wiring)."""
    return [View(Switches(), size) for _ in shows]


def graph(shows, src: Any = None, effects: tuple[str, ...] = (), clouds: tuple[str, ...] = (),
          size=(10, 10), **kw) -> G.Graph:
    """The frame `src` draws on one window per state of `shows`."""
    return G.build_graph(views(shows, size), wiring(src, *shows, **kw), tuple(clouds),
                         tuple(effects))
