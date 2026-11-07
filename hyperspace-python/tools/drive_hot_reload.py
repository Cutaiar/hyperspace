"""tools/app_driver.py script: a hot reload in the real app (HR, row 802). Touches
files the way a save does and says what the reloader said, then checks every live
object it holds is on the class its module now has, and that a hook landed.

    uv run python tools/app_driver.py tools/drive_hot_reload.py --out <scratch>/run --every 1000

`HYPERSPACE_TOUCH` names the modules, comma separated (default the four the fault
was found on). tests/test_hot_reload_app.py runs this with the first module on the
list, so all of them reload. Anything wrong leaves through an exception: the driver
exits 1 and says why. The last line on stdout is `reloaded: <modules>` when all is well.
"""

import os
import sys
from pathlib import Path

import hyperspace
from hyperspace.hotreload import MODULES

TOUCH = ("outputs", "render", "ghost", "ui")


def _file(name: str) -> Path:
    return Path(hyperspace.__file__).parent / f"{name.replace('.', '/')}.py"


def stale(reloader) -> list[str]:
    """Every live object not on the class its module now has."""
    out = []
    for obj, mod, cls in reloader.targets():
        now = getattr(sys.modules[f"hyperspace.{mod}"], cls)
        if type(obj) is not now:
            out.append(f"{mod}.{cls}")
    return sorted(set(out))


def script(d, panel):
    reloader = panel.reloader
    names = os.environ.get("HYPERSPACE_TOUCH", ",".join(TOUCH)).split(",")
    renderer = panel.meta.decks[0].renderer
    yield from d.wait(5)
    for name in names:
        lines = renderer._lines                     # what `Renderer.on_reload` makes again
        reloader.status, reloader.error = "", ""
        os.utime(_file(name))                       # saved, as far as the reloader can tell
        for _ in range(4000):                       # (a frame; the poll's period is 0.5 s)
            if reloader.status.startswith("hot:") or reloader.error:
                break
            yield
        print(f"touch {name}: error={reloader.error!r} status={reloader.status!r} "
              f"restart={reloader.restart!r}", flush=True)
        assert not reloader.error, f"touching {name}: {reloader.error}"
        assert reloader.status.startswith("hot:"), f"touching {name}: no reload seen"
        wrong = stale(reloader)
        assert not wrong, f"touching {name} left these on an old class: {wrong}"
        # the hook: a render module's save compiles new programs on the live renderer
        reran = renderer._lines is not lines
        print(f"  hook: Renderer.on_reload {'ran' if reran else 'not due'}; "
              f"{len(reloader.targets())} targets on today's classes", flush=True)
        if MODULES.index(name) <= MODULES.index("render"):   # (a later module's save leaves it)
            assert reran, f"touching {name}: Renderer.on_reload did not run"
        yield from d.wait(5)                        # the frames after the swap draw
        assert not reloader.runtime_error, f"after {name}: {reloader.runtime_error}"
    for deck in panel.meta.decks:                   # the views came through with their own state
        lib = deck.loaded_patch.lib
        assert lib.own is deck.loaded_patch and lib.project.lib is lib
    print(f"reloaded: {','.join(names)}", flush=True)
