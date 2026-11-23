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

The same dialog saves too (plan 88): **save to location…** under **save as**'s ▾
opens it in save mode (`open_save`) on the folder of the patch the panel's
deck holds, else the patches' folder (on the owner's Mac, the library is in
Google Drive, so that is ``My Drive/Hyperspace/loadable``). The folder picked
is the patch's folder (a new one made in the dialog too) and the file name
typed its name (`save_name`); a place outside the library's patches folder
is refused in words, as a pick is, since no load, pad or list would find a
patch there. The save is `Install.save_named`'s, which never writes over a
file.

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
SAVE_KEY = "hyperspace.patches.save"  # …and for its save mode
SAVE_TITLE = "Save the deck as a new patch"
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
        st = panel._browse = {"open": None, "native": None, "saving": False}
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
    """A dialog is up, to load or to save."""
    st = _state(panel)
    return st["open"] is not None or st["native"] is not None


def is_loading(panel) -> bool:
    """The dialog that is up is **load…**'s (its chip is lit for it)."""
    return is_open(panel) and not _state(panel).get("saving", False)


def is_saving(panel) -> bool:
    """The dialog that is up is **save to location…**'s."""
    return is_open(panel) and _state(panel).get("saving", False)


def open_patches(panel) -> None:
    """Open the explorer on the patches (one at a time: a second ask while
    one is up does nothing)."""
    lib, st = panel.library, _state(panel)
    if lib is None or is_open(panel):
        return
    st["saving"] = False
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


def open_save(panel) -> None:
    """Open the dialog in save mode (plan 88, the module docstring): on the folder
    of the patch the panel's deck holds, else the patches' folder; the name the
    one-press save would give is typed in for you. One at a time, as `open_patches`."""
    lib, st = panel.library, _state(panel)
    if lib is None or is_open(panel):
        return
    st["saving"] = True
    where = start_dir(lib)
    leaf = lib.install.next_save_name().rsplit("/", 1)[-1]
    if _setup():
        from imgui_bundle import im_file_dialog as ifd

        fd = ifd.FileDialog.instance()
        base = str(loadable_dir(lib.home))
        if base not in [str(f) for f in fd.get_favorites()]:
            fd.add_favorite(base)
        try:
            if fd.save(SAVE_KEY, SAVE_TITLE, FILTER, str(where)):
                st["open"] = SAVE_KEY
                return
        except RuntimeError as e:           # an imgui assert, raised: the native one
            _ifd.update(ok=False, why=str(e))
    try:
        from imgui_bundle import portable_file_dialogs as pfd

        st["native"] = pfd.save_file(SAVE_TITLE, str(where / f"{leaf}.json"),
                                     ["Patches", "*.json"])
    except Exception as e:  # noqa: BLE001 — a dialog is best effort
        st["saving"] = False
        lib.say(warning=f"save: no file dialog ({e})")


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
                _answer(panel, Path(picked))
    native = st["native"]
    if native is not None and native.ready():
        st["native"] = None
        picked = native.result()        # a list from open_file, a str from save_file
        if isinstance(picked, str):
            picked = [picked] if picked else []
        if picked:
            _answer(panel, Path(picked[0]))


def _answer(panel, path: Path) -> None:
    if _state(panel).get("saving", False):
        save_at(panel, path)
    else:
        take(panel, path)


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


def save_name(lib, path: Path) -> str | None:
    """The patch name a file picked in the save dialog stands for: its folder under
    the patches' folder and its file name less ``.json`` (``party/moo final``);
    None for a place outside that folder."""
    base = loadable_dir(lib.home)
    path = Path(path)
    stem = path.name[:-5] if path.name.lower().endswith(".json") else path.name
    try:
        rel = path.parent.resolve().relative_to(base.resolve())
    except (ValueError, OSError):
        return None
    folder = rel.as_posix()
    if not stem.strip():
        return None
    return stem if folder in ("", ".") else f"{folder}/{stem}"


def save_at(panel, path: Path) -> str | None:
    """Save the panel's deck as a new patch at `path`, picked in the save dialog
    (`Install.save_named`: never over a file); the new name, or None with why on
    the warning line."""
    from . import ui_loadable

    lib = panel.library
    if Path(path).exists():             # a file picked to write over: never
        lib.say(warning=f"{Path(path).name}: not saved — that file is there already; "
                        "nothing is written over, so type a new name")
        return None
    name = save_name(lib, path)
    if name is None:
        lib.say(warning=f"{path}: not saved — a patch saves under the library's "
                        f"patches folder, {loadable_dir(lib.home)}, where load… and "
                        "the pads can find it")
        return None
    return ui_loadable.save_named(panel, name)


def chip(panel) -> bool:
    """The **load…** chip on GRAPH's deck row; True when pressed (the dialog
    is then open). Lit while the dialog is up."""
    from . import ui

    hit = ui.lit_chip(f"{LABEL}##graph.load", is_loading(panel))
    if imgui.is_item_hovered():
        ui.tooltip(TIP)
    if hit:
        open_patches(panel)
    return hit
