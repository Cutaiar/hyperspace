"""Choosing a patch to load — a meta controller verb, so it lives on GRAPH's
deck row (ui_graph._deck_row: deck · **load…** · copy on air to off air ·
fade), not in the side pane.

**load…** opens the patches' folder in Dear ImGui's file dialog
(ImFileDialog, in imgui-bundle), on the folder the off-air deck's patch
sits in: folders to step into, the path to step back up, a search field,
new folder, rename and delete on a right-click, the library's folder
pinned under Quick Access. A pick loads that patch onto the deck **off
air**, by the pads' road (`DeckInstall.load_named`: refused while the
crossfader is between its ends); the fade takes it on air. With no meta
controller (a test's panel) it loads onto the panel's deck.

The dialog lists **files**, by file name (``party-tumble.json``), not
patches by the name inside (``TUMBLE``): the pick is mapped back to the
listed name (`Library.name_at`), and a file that is no patch of this
library is refused in words. A file moved or a folder renamed there (or in
Finder) is followed by the library (`Library._hand_moves`); its delete is
the dialog's own, for good, never the app's trash.

ImFileDialog draws its icons through a texture loader that imgui-bundle
sets only under its own runners, and has no Python name for. `_setup`
calls the bundle's own setup function by its symbol, after the GL loader
its textures need (`hello_imgui.init_gl_loader`, made for a host like this
one). Where that fails — a wheel that does not export the symbol — the
native dialog (portable_file_dialogs, as MEDIA's and AUDIO's) opens on the
same folder and the pick is handled the same way.

`draw` runs every frame from `Panel._draw`: the dialog is a window of its
own and must be drawn (and its answer taken) whatever GRAPH shows.
`scrub` runs before the frame is rendered (app.py), for the reason it
gives.
"""

from __future__ import annotations

import ctypes
import importlib
from pathlib import Path

from imgui_bundle import imgui

from .library import LOADABLE, LibraryError, loadable_dir

KEY = "hyperspace.patches"            # ImFileDialog's key for this dialog
TITLE = "Load a patch off air"
LABEL = "load…"
FILTER = "Patches (*.json){.json},.*"
SETUP = "_Z30ImFileDialogSetupTextureLoaderv"    # ImFileDialogSetupTextureLoader()
TIP = ("Pick a patch from the library's folders: it loads on the deck off air, and the "
       "fade takes it on air. Files are listed by file name; right-click in the list for "
       "new folder, rename and delete (delete is for good)")

_ifd: dict = {}       # {"ok": bool, "why": str} once `_setup` has run


def _setup() -> bool:
    """ImFileDialog's texture loader, set once (the module docstring);
    False, with why in ``_ifd["why"]``, when it could not be."""
    if "ok" not in _ifd:
        try:
            from imgui_bundle import hello_imgui
            from imgui_bundle import im_file_dialog as _  # noqa: F401 — it is in this build

            native = importlib.import_module("imgui_bundle._imgui_bundle")   # the one .so

            if not hello_imgui.init_gl_loader():
                raise RuntimeError("no GL loader in this imgui-bundle")
            fn = getattr(ctypes.CDLL(native.__file__), SETUP)
            fn.restype = None
            fn()
            _ifd.update(ok=True, why="")
        except Exception as e:  # noqa: BLE001 — best effort: the native dialog stands in
            _ifd.update(ok=False, why=f"{type(e).__name__}: {e}")
    return _ifd["ok"]


def _state(panel) -> dict:
    st = getattr(panel, "_browse", None)
    if st is None:
        st = panel._browse = {"open": None, "native": None}
    return st


def _target(panel):
    """The library view of the deck a pick lands on: the deck off air's
    (the meta controller's), else the panel's own."""
    meta = getattr(panel, "meta", None)
    where = meta.off_air_project() if meta is not None else None
    return where.lib if where is not None else panel.library


def start_dir(lib) -> Path:
    """Where the dialog opens: the folder the deck's patch file is in,
    else the patches' folder."""
    base = loadable_dir(lib.home)
    cur = lib.current(LOADABLE)
    try:
        path = lib.path_of(LOADABLE, cur) if cur else None
    except (LibraryError, OSError):
        path = None
    return path.parent if path is not None and path.parent.is_dir() else base


def is_open(panel) -> bool:
    st = _state(panel)
    return st["open"] is not None or st["native"] is not None


def open_patches(panel) -> None:
    """Open the explorer on the patches (one at a time: a second ask while
    one is up does nothing)."""
    lib, st = panel.library, _state(panel)
    if lib is None or is_open(panel):
        return
    where = start_dir(_target(panel))
    if _setup():
        from imgui_bundle import im_file_dialog as ifd

        fd = ifd.FileDialog.instance()
        base = str(loadable_dir(lib.home))
        if base not in [str(f) for f in fd.get_favorites()]:
            fd.add_favorite(base)
        try:
            if fd.open(KEY, TITLE, FILTER, False, str(where)):
                st["open"] = KEY
                return
        except RuntimeError as e:           # an imgui assert, raised: the native one
            _ifd.update(ok=False, why=str(e))
    try:
        from imgui_bundle import portable_file_dialogs as pfd

        st["native"] = pfd.open_file(TITLE, str(where), ["Patches", "*.json"])
    except Exception as e:  # noqa: BLE001 — a dialog is best effort
        lib.say(warning=f"browse: no file dialog ({e})")


def draw(panel) -> None:
    """Each frame: draw the dialog while it is up, and take its answer."""
    st = _state(panel)
    if st["open"] is not None:
        from imgui_bundle import im_file_dialog as ifd

        fd = ifd.FileDialog.instance()
        if fd.is_done(st["open"]):
            picked = fd.get_result().path() if fd.has_result() else None
            fd.close()
            st["open"] = None
            st["shut"] = True           # (`scrub` looks at this frame too)
            if picked:
                take(panel, Path(picked))
    native = st["native"]
    if native is not None and native.ready():
        st["native"] = None
        picked = native.result()
        if picked:
            take(panel, Path(picked[0]))


def scrub(panel, draw_data) -> int:
    """Before the frame is rendered, while the dialog is up (and the frame
    it shut): empty every draw command whose texture is no longer one, and
    point it at a texture that is. ImFileDialog deletes a folder's icon
    textures the moment another folder is opened — mid-frame, with rows
    already drawn with them — and this renderer, unlike the C++ ones,
    raises on binding a deleted texture (PyOpenGL checks every call, and it
    binds for an empty command too): the app would stop on a double-click.
    The icons are missing for that one frame. Returns how many it emptied.
    Nothing is looked at with no dialog up."""
    st = _state(panel)
    if st["open"] is None and not st.pop("shut", False):
        return 0
    from OpenGL import GL

    alive: dict[int, bool] = {}
    good, dead = None, []
    for cmds in draw_data.cmd_lists:
        buf = cmds.cmd_buffer
        for i in range(buf.size()):
            cmd = buf[i]                # (by index: iterating hands out copies)
            tex = int(cmd.tex_ref.get_tex_id())
            if tex not in alive:
                alive[tex] = bool(GL.glIsTexture(tex))
            if not alive[tex]:
                dead.append(cmd)
            elif good is None:
                good = cmd.tex_ref
    for cmd in dead:
        cmd.elem_count = 0
        if good is not None:
            cmd.tex_ref = good
    return len(dead)


def take(panel, path: Path) -> str | None:
    """Load the patch whose file is `path` and return its name; a file that
    is no patch of this library is refused on the warning line."""
    from . import ui_loadable

    lib = panel.library
    name = lib.name_at(path)
    if name is None:
        lib.say(warning=f"{path.name}: not a patch in this library — "
                        f"its patches are under {loadable_dir(lib.home)}")
        return None
    meta = getattr(panel, "meta", None)
    where = meta.off_air_project() if meta is not None else None
    if meta is not None:
        if where is None:
            lib.say(warning=f"{name}: not loaded — there is no deck off air to load")
            return None
        got = where.load_named(name)
    else:
        got = name if ui_loadable._guard(panel, lib.load, LOADABLE, name) is not None else None
    ui_loadable.invalidate(panel, LOADABLE)
    return got


def chip(panel) -> bool:
    """The **load…** chip on GRAPH's deck row; True when pressed (the dialog
    is then open). Lit while the dialog is up."""
    from . import ui

    hit = ui.lit_chip(f"{LABEL}##graph.load", is_open(panel))
    if imgui.is_item_hovered():
        ui.tooltip(TIP)
    if hit:
        open_patches(panel)
    return hit
