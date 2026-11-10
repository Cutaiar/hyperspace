"""The app's loadable patch half with no window, no audio and no GL: the registry,
the library, the router (with the LFO, envelope and sequencer banks) and
`loadable.LoadedPatch`, as app.main wires them — what the tests load and save
loadable patches through (tests/test_plan31_wiring.make_app) and what
tools/migrate_library.py rewrites a library with (row 394).

`resave` is the one road a file takes there: copied into a scratch library
as a user's loadable patch, loaded by the library, saved untouched under the name
it loaded as (`Library.save_as`, the strip's save), the bytes written read
back. Nothing here touches the library a file came from.

Plan 43 C2: a resave is the migration's, so it writes the spin's pose only
where the file had one (the app saves one every time; the resave takes it
back out of a file that had none — an old file keeps spinning, and its
`/9` is a fixed point); and with `show` — what an old show kept of
the camera (`show_seed`) — the scratch library opens a show holding just
that, so an old loadable patch takes the meta controller's eye as the app takes it.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from types import SimpleNamespace

from . import envelope, grip, lfo, loadable, routing, sequencer, tempo
from .analysis import Analyser
from .analyzer import Analyzer
from .control import Control
from .envelope import Envelopes
from .fx import FxState
from .lfo import LFOs
from .library import Library, slug
from .lookback import DreamState
from .params import build_registry
from .sequencer import Sequencer
from .view import ViewState


def make_app(home: Path, plan31: bool = True, *, machine: Path | None = None):
    """The app's registry, library, router and loadable patches over the library at
    `home` (`machine`: the home for this machine's files — bindings.json,
    last_show — default `home`); `plan31` False is a build from before plan
    31 — no envelopes, no sequencer."""
    home = Path(home)
    machine = home if machine is None else Path(machine)
    chain = Analyzer(Analyser())
    control = Control(chain)
    lib = Library(home, period=0.0) if machine == home else Library(
        home, machine=machine, period=0.0)
    reg = build_registry(ViewState(), control, SimpleNamespace(chain=chain), lib.install,
                         dream=DreamState(), fx=FxState())
    control.library = lib
    clock = tempo.Clock(now=lambda: 0.0)
    lfos, envs, seq = LFOs(), Envelopes(), Sequencer()
    tempo.register(reg, clock)
    lfo.register(reg, lfos, clock)
    grip.register(reg, grip.GripState())     # plan 60: a patch's own, as `Deck.build` registers it
    if plan31:
        envelope.register(reg, envs, clock)
        sequencer.register(reg, seq, clock)
    table = routing.Bindings.load(routing.bindings_path(machine), legacy_midi=None)
    routing.register_desk(reg, table)
    lib.attach(reg)
    router = routing.Router(reg, table)
    router.use_lfos(lfos, clock)
    if plan31:
        router.use_bank(envs, clock)
        router.use_sequencer(seq, envs)
    loaded_patch = loadable.LoadedPatch(lib, reg, router)
    return SimpleNamespace(lib=lib, reg=reg, router=router, loaded_patch=loaded_patch, lfos=lfos,
                           envs=envs, seq=seq, clock=clock)


# the library folders copied beside a loadable patch for its load: the module
# loadable patches (a strip's defaults; plan 44 D3 retired the desk templates and
# the labels, so a whole loadable patch's load reads none of them, but the golden
# meta controller and the tools keep the library's module groups as the app has them).
# Plan 50 (review fix 2): every module preset is a patch of one group under
# `patches/<group>/`, so the one folder, every folder down (`copytree`) —
# the old `<group>/` folders are the migration's to move, never read
SHARED_FOLDERS = ("patches",)
def _link_or_copy(src, dst):
    """A hard link where the disk allows one, else a copy."""
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)
    return dst


SEED_SHOW = "migration"        # the scratch show `seed` writes (plan 43 C2)


def show_seed(doc: dict | None, eye: dict | None = None,
              camera_at: list | None = None, look: dict | None = None,
              cuts=None) -> dict | None:
    """What an old show kept of the look, as a show of its own: its
    meta controller's `eye.*` and its layout's camera node (plan 43 C2,
    `library.show_eye`), and (plan 44 D3) the hands' and clouds' looks in
    its session and its bus cuts (`library.show_look`) — nothing else of
    the meta controller: what an old loadable patch drew through. `eye` / `camera_at` / `look`
    / `cuts` stand in where `doc` kept none (a `.bak-v2-eye` or
    `.bak-v2-look` copy's, `library.kept_eye` / `kept_look`). Written as a
    `/2` show, so the app reads it as the old show it stands for
    (`Install.old_eye`, `old_look`, `old_cuts`). None when there is
    nothing: an old loadable patch takes the build's defaults."""
    from .graphmigrate import CAMERA_NODE
    from .library import PROJECT_V2, RIG, show_eye, show_look
    own_eye, own_at = show_eye(doc)
    own_look, own_cuts = show_look(doc)
    eye = own_eye or dict(eye or {})
    at = own_at if own_at is not None else camera_at
    look = own_look or dict(look or {})
    cuts = own_cuts if own_cuts.cut else cuts
    cut = cuts.to_json() if cuts is not None and getattr(cuts, "cut", None) else {}
    if not eye and at is None and not look and not cut:
        return None
    out: dict = {"schema": PROJECT_V2, "name": SEED_SHOW, "session": {**look, **eye}}
    if at is not None:
        out["layout"] = {CAMERA_NODE: list(at)}
    if cut:
        out[RIG] = cut
    return out


def seed(home: Path, machine: Path, show: dict | None) -> None:
    """Open `show` (a `show_seed`) at the next launch over the library at
    `home`: written as ``projects/migration.hyp.json`` and named in the
    machine's ``last_show``. None writes nothing."""
    if not show:
        return
    from .library import LAST_SHOW, PROJECT_SUFFIX, PROJECTS
    folder = Path(home) / PROJECTS
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{SEED_SHOW}{PROJECT_SUFFIX}").write_text(json.dumps(show))
    Path(machine).mkdir(parents=True, exist_ok=True)
    (Path(machine) / LAST_SHOW).write_text(f"{SEED_SHOW}\n")


def resave(path: Path, scratch: Path, *, library: Path | None = None,
           show: dict | None = None) -> tuple[bytes, list[str], str]:
    """Preset file `path` loaded and saved untouched by the app (`make_app`)
    in a scratch library at `scratch` — `path` copied in as a loadable patch of its
    own, with `library`'s module presets beside it when
    given, and `show` (a `show_seed`: the meta controller's old eye) open: (the bytes
    the save wrote, the load's notes, the name it loaded as). The pose is
    written only where the file had one. Raises
    what the load raises (`LibraryError`) for a file that does not load.
    `scratch` is created; nothing outside it is written."""
    scratch = Path(scratch)
    home, machine = scratch / "library", scratch / "machine"
    (home / loadable.GROUP).mkdir(parents=True, exist_ok=True)
    machine.mkdir(parents=True, exist_ok=True)
    if library is not None:
        for folder in SHARED_FOLDERS:
            src = Path(library) / folder
            if src.is_dir():
                # (hard links where the disk allows: a library's folders are
                # read, never written, by a resave — one copy per run, not
                # one per loadable patch; review 2.7)
                shutil.copytree(src, home / folder, dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns(".*", "Icon*"),
                                copy_function=_link_or_copy)
    before = os.environ.get("HYPERSPACE_HOME")
    os.environ["HYPERSPACE_HOME"] = str(machine)    # (nothing reaches ~/Hyperspace)
    try:
        # (copied under its slug: a file name the library would not write —
        # `factory--dial.json`, `My Look.json` — still loads by it)
        stem = slug(Path(path).stem)
        shutil.copyfile(path, home / loadable.GROUP / f"{stem}.json")
        seed(home, machine, show)
        app = make_app(home, machine=machine)
        app.lib.load(loadable.GROUP, stem)
        name = app.lib.current(loadable.GROUP) or stem
        notes = list(app.loaded_patch.notes)
        out = app.loaded_patch.save_as(name)
        # (plan 43 C2: the app saves the pose every time; the migration
        # writes one only where the file had one — an old file keeps
        # spinning — so a file without one has it taken back out)
        try:
            had = loadable.POSE_KEY in json.loads(Path(path).read_text())
        except (OSError, ValueError, TypeError):
            had = True
        if not had:
            doc = json.loads(out.read_text())
            if doc.pop(loadable.POSE_KEY, None) is not None:
                out.write_text(loadable.dumps(doc))
        return out.read_bytes(), notes, name
    finally:
        if before is None:
            os.environ.pop("HYPERSPACE_HOME", None)
        else:
            os.environ["HYPERSPACE_HOME"] = before
