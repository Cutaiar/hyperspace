"""Choosing a patch to load is the meta controller's (ui_browse.py): **load…**
on GRAPH's deck row opens the library's folders in a file dialog, and a pick
lands on the deck off air by the pads' road — never the room, refused while
the crossfader is between its ends. Nothing in the side pane lists a patch
to load (test_ui_loadable)."""

from types import SimpleNamespace

from test_ui_shell import frame, rig  # noqa: F401 — the fixture

from hyperspace import ui_browse
from hyperspace.library import LOADABLE


def _folder(lib, folder: str, names: list[str]) -> None:
    d = lib.home / "loadable" / folder
    d.mkdir(parents=True, exist_ok=True)
    for n in names:
        src = lib.path_of(LOADABLE, n)
        src.rename(d / src.name)
    lib._sync()


def test_a_picked_file_loads_by_its_listed_name_and_a_stranger_is_refused(rig):  # noqa: F811
    """No meta controller (the rig's panel): the pick lands on the panel's
    deck. A file that is no patch of this library is refused in words."""
    panel, lib = rig.panel, rig.lib
    _folder(lib, "party", ["DIAL"])
    assert ui_browse.take(panel, lib.home / "loadable" / "party" / "dial.json") == "party/DIAL"
    assert lib.current(LOADABLE) == "party/DIAL"
    assert ui_browse.take(panel, lib.home / "installs" / "nope.json") is None
    assert "not a patch in this library" in lib.warning
    assert lib.current(LOADABLE) == "party/DIAL"
    # with no dialog up, the frame's draw lists are not looked at
    assert ui_browse.scrub(panel, None) == 0 and not ui_browse.is_open(panel)


def test_the_dialog_opens_on_the_folder_of_the_decks_patch(rig):  # noqa: F811
    lib = rig.lib
    _folder(lib, "party", ["DIAL"])
    assert ui_browse.start_dir(lib) == lib.home / "loadable"          # nothing loaded
    lib.load(LOADABLE, "party/DIAL")
    assert ui_browse.start_dir(lib) == lib.home / "loadable" / "party"


class _Where:
    """A deck off air's bank view, as `MetaController.off_air_project` hands it."""

    def __init__(self, refuse: str | None = None):
        self.loaded, self.refuse = [], refuse
        self.lib = SimpleNamespace(say=lambda **k: None)

    def load_named(self, name):
        if self.refuse:
            return None
        self.loaded.append(name)
        return name


def test_with_a_meta_controller_a_pick_lands_off_air(rig):  # noqa: F811
    panel, lib = rig.panel, rig.lib
    where = _Where()
    panel.meta = SimpleNamespace(off_air_project=lambda: where)
    was = lib.current(LOADABLE)
    path = lib.path_of(LOADABLE, "TRIP")
    assert ui_browse.take(panel, path) == "TRIP"
    assert where.loaded == ["TRIP"] and lib.current(LOADABLE) == was     # the panel's deck kept
    panel.meta = SimpleNamespace(off_air_project=lambda: None)
    assert ui_browse.take(panel, path) is None
    assert "no deck off air" in lib.warning
    panel.meta = None


def test_load_named_goes_by_the_pads_road(rig):  # noqa: F811
    """`DeckInstall.load_named`: the deck `row_load` names, refused (said)
    while the fader is between its ends."""
    from hyperspace.library import DeckInstall

    said, loaded = [], []
    deck = SimpleNamespace(current=None)

    def load(name):
        loaded.append(name)
        deck.current = name
    deck.load = load
    target = SimpleNamespace(_loader=lambda: deck, lib=SimpleNamespace(error=""))
    inst = DeckInstall.__new__(DeckInstall)
    object.__setattr__(inst, "lib", SimpleNamespace(say=lambda **k: said.append(k)))
    object.__setattr__(inst, "meta", SimpleNamespace(
        row_load=lambda: (target, None), loaded_words=lambda n: f"{n} loaded off air"))
    target.lib.say = lambda **k: said.append(k)
    assert inst.load_named("TRIP") == "TRIP" and loaded == ["TRIP"]
    assert said[-1] == {"status": "TRIP loaded off air"}
    object.__setattr__(inst, "meta", SimpleNamespace(row_load=lambda: (None, "between its ends")))
    assert inst.load_named("WAKE") is None and loaded == ["TRIP"]
    assert "between its ends" in said[-1]["warning"]
