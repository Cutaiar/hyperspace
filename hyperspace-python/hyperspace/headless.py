"""The app's preset half with no window, no audio and no GL: the registry,
the library, the router (with the LFO, envelope and sequencer banks) and
`preset.Presets`, as app.main wires them — what the tests load and save
presets through (tests/test_plan31_wiring.make_app) and what
tools/migrate_library.py rewrites a library with (row 394).

`resave` is the one road a file takes there: copied into a scratch library
as a user's preset, loaded by the library, saved untouched under the name
it loaded as (`Library.save_as`, the strip's save), the bytes written read
back. Nothing here touches the library a file came from.
"""

from __future__ import annotations

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


def resave(path: Path, scratch: Path, *, library: Path | None = None
           ) -> tuple[bytes, list[str], str]:
    """Preset file `path` loaded and saved untouched by the app (`make_app`)
    in a scratch library at `scratch` — `path` copied in as a preset of its
    own, with `library`'s desk templates and module presets beside it when
    given: (the bytes the save wrote, the load's notes, the name it loaded
    as). Raises what the load raises (`LibraryError`) for a file that does
    not load. `scratch` is created; nothing outside it is written."""
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
        app = make_app(home, machine=machine)
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
