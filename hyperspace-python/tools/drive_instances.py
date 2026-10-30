"""tools/app_driver.py's example script: the instanced field on the VIEW
page, by mouse and keys — the count typed in, Fit, a lattice picked from
the Layout menu, its depth dragged, then 4096 copies of CUBIC.

    uv run python tools/app_driver.py tools/drive_instances.py --out /tmp/instances
"""

from hyperspace.field import NAMES
from hyperspace.ui import PAGE_KEYS


def script(d, panel):
    reg = panel.reg
    reg["camera.zoom"].set_value(1.0)          # a known camera, whatever the home opened on
    reg["camera.yaw"].set_value(0.45)
    reg["camera.pitch"].set_value(0.3)
    yield from d.click(f"page{PAGE_KEYS.index('view')}", frames=20)     # the VIEW tab
    yield from d.wait(20)
    yield from d.enter("view.instances", 12, frames=20)
    yield from d.park()
    yield from d.wait(40)
    yield from d.click("view.inst_fit", frames=20)
    yield from d.park()
    yield from d.wait(60)
    yield from d.pick("view.inst_layout", NAMES.index("FCC"), frames=20)
    yield from d.park()
    yield from d.wait(40)
    yield from d.enter("view.instances", 153, frames=20)     # the count taper's detent: 299
    yield from d.park()
    yield from d.wait(40)
    yield from d.slide("view.inst_persp", 1.0, frames=30)
    yield from d.slide("view.inst_persp", 0.15, frames=30)
    yield from d.park()
    yield from d.wait(40)
    yield from d.pick("view.inst_layout", NAMES.index("CUBIC"), frames=20)
    yield from d.enter("view.instances", 304, frames=20)     # the top: 4096
    yield from d.park()
    yield from d.wait(90)
