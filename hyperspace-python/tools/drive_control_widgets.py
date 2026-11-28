"""tools/app_driver.py script for the control widgets: Zoom burst's
XYZ volume dragged and its knobs turned, then Kaleidoscope's strip —
Segments' ticks, Swirl's bipolar fill and detent, Zoom's unity detent.

    uv run python tools/app_driver.py tools/drive_control_widgets.py --out /tmp/widgets
"""

from hyperspace.ui import PAGE_KEYS


def script(d, panel):
    panel.library.loaded_patch.load("TRIP")
    yield from d.wait(10)
    panel.reg["ui.page"].set(PAGE_KEYS.index("fx"))
    panel.fx_selected = "zoomblur"
    yield from d.wait(20)
    yield from d.reveal("fx.zoomblur.amount")       # the volume's last knob, so all of it shows
    yield from d.wait(4)
    x0, y0, x1, y1 = d.rect("pad.fx.zoomblur.cx")
    w, h = x1 - x0, y1 - y0
    yield from d.move((x0 + w * 0.5, y0 + h * 0.5), 10)
    yield from d.press(True)
    for fx_, fy in ((0.7, 0.3), (0.8, 0.6), (0.3, 0.75), (0.25, 0.3)):
        yield from d.move((x0 + w * fx_, y0 + h * fy), 15)
    yield from d.press(False)
    yield from d.wait(10)
    x, y = d.centre("fx.zoomblur.amount")
    yield from d.move((x, y), 10)
    yield from d.press(True)
    yield from d.move((x, y - 60), 15)
    yield from d.press(False)
    yield from d.park()
    yield from d.wait(20)
    panel.fx_selected = "kaleido"
    yield from d.wait(20)
    yield from d.reveal("fx.kaleido.swirl")
    yield from d.wait(10)
    yield from d.slide("fx.kaleido.swirl", 0.8, frames=20)
    yield from d.park()
    yield from d.wait(20)
    yield from d.slide("fx.kaleido.segments", 0.6, frames=20)
    yield from d.park()
    yield from d.wait(20)
