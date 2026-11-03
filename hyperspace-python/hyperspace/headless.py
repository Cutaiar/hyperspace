"""The app's preset half with no window, no audio and no GL: the registry,
the library, the router (with the LFO, envelope and sequencer banks) and
`preset.Presets`, as app.main wires them — what the tests load and save
presets through (tests/test_plan31_wiring.make_app) and what
tools/migrate_library.py rewrites a library with (row 394).

`resave` is the one road a file takes there: copied into a scratch library
as a user's preset, loaded by the library, saved untouched under the name
it loaded as (`Library.save_as`, the strip's save), the bytes written read
back. Nothing here touches the library a file came from.

Plan 43 C2: a resave is the migration's, so it writes the spin's pose only
where the file had one (`Presets.pose_of_file`: an old file keeps spinning,
and its `/9` is a fixed point); and with `show` — what an old show kept of
the camera (`show_seed`) — the scratch library opens a show holding just
that, so an old preset takes the rig's eye as the app takes it.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from types import SimpleNamespace

from . import envelope, lfo, preset, routing, sequencer, tempo
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
    """The app's registry, library, router and presets over the library at
    `home` (`machine`: the home for this machine's files — bindings.json,
    last_show — default `home`); `plan31` False is a build from before plan
    31 — no envelopes, no sequencer."""
    home = Path(home)
    machine = home if machine is None else Path(machine)
    chain = Analyzer(Analyser())
    control = Control(chain)
    lib = Library(home, period=0.0) if machine == home else Library(
        home, machine=machine, period=0.0)
    reg = build_registry(ViewState(), control, SimpleNamespace(chain=chain), lib.project,
                         dream=DreamState(), fx=FxState())
    control.library = lib
    clock = tempo.Clock(now=lambda: 0.0)
    lfos, envs, seq = LFOs(), Envelopes(), Sequencer()
    tempo.register(reg, clock)
    lfo.register(reg, lfos, clock)
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
    presets = preset.Presets(lib, reg, router)
    return SimpleNamespace(lib=lib, reg=reg, router=router, presets=presets, lfos=lfos,
                           envs=envs, seq=seq, clock=clock)


# the library folders a preset's load reads beside its own file: the desk
# templates it may name (plan 24 C3) and the module presets it labels
SHARED_FOLDERS = ("desk", "fx", "dream", "band", "tempo")
SEED_SHOW = "migration"        # the scratch show `seed` writes (plan 43 C2)


def show_seed(doc: dict | None) -> dict | None:
    """What an old show (before plan 43 C2) kept of the camera, as a show of
    its own: its session's `eye.*` and its layout's camera node — nothing
    else of the rig (plan 43 C2: the eye an old preset drew through). None
    when it kept neither (a show from C2 on, or no show): nothing to seed,
    so an old preset takes the build's default eye."""
    if not isinstance(doc, dict):
        return None
    from .graphmigrate import CAMERA_NODES
    from .library import CAMERA_NODE, EYE_IDS, PROJECT_SCHEMA, read_layout
    session = doc.get("session") if isinstance(doc.get("session"), dict) else {}
    layout, _ = read_layout(doc.get("layout"))
    out: dict = {"schema": PROJECT_SCHEMA, "name": SEED_SHOW,
                 "session": {pid: session[pid] for pid in EYE_IDS if pid in session}}
    at = next((layout[k] for k in CAMERA_NODES if k in layout), None)
    if at is not None:
        out["layout"] = {CAMERA_NODE: at}
    return out if out["session"] or at is not None else None


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
    in a scratch library at `scratch` — `path` copied in as a preset of its
    own, with `library`'s desk templates and module presets beside it when
    given, and `show` (a `show_seed`: the rig's old eye) open: (the bytes
    the save wrote, the load's notes, the name it loaded as). The pose is
    written only where the file had one (`Presets.pose_of_file`). Raises
    what the load raises (`LibraryError`) for a file that does not load.
    `scratch` is created; nothing outside it is written."""
    scratch = Path(scratch)
    home, machine = scratch / "library", scratch / "machine"
    (home / preset.GROUP).mkdir(parents=True, exist_ok=True)
    machine.mkdir(parents=True, exist_ok=True)
    if library is not None:
        for folder in SHARED_FOLDERS:
            src = Path(library) / folder
            if src.is_dir():
                shutil.copytree(src, home / folder, dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns(".*", "Icon*"))
    before = os.environ.get("HYPERSPACE_HOME")
    os.environ["HYPERSPACE_HOME"] = str(machine)    # (nothing reaches ~/Hyperspace)
    try:
        # (copied under its slug: a file name the library would not write —
        # `factory--dial.json`, `My Look.json` — still loads by it)
        stem = slug(Path(path).stem)
        shutil.copyfile(path, home / preset.GROUP / f"{stem}.json")
        seed(home, machine, show)
        app = make_app(home, machine=machine)
        app.presets.pose_of_file = True
        app.lib.load(preset.GROUP, stem)
        name = app.lib.current(preset.GROUP) or stem
        notes = list(app.presets.notes)
        out = app.presets.save_as(name)
        return out.read_bytes(), notes, name
    finally:
        if before is None:
            os.environ.pop("HYPERSPACE_HOME", None)
        else:
            os.environ["HYPERSPACE_HOME"] = before
