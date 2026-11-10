"""tools/app_driver.py script (plan 59, hand checks 659-660): the world-check
patches, built in the real app and saved through its own save, each held a
while for the screenshots; then Reset world pressed on the first.

    uv run python tools/app_driver.py tools/drive_world_check.py --out /tmp/wc

The saved files land in OUT/patches (OUT from WC_OUT, else /tmp/world-check);
tests/fixtures/world-check/ holds them. A home whose config lists a hand tape
([[devices]] kind = "hands", tape = …) shows hands in the shots.
"""

import json
import os
import shutil
from pathlib import Path

from hyperspace.ui import PAGE_KEYS

OUT = Path(os.environ.get("WC_OUT", "/tmp/world-check"))
FOLDER = "world check"

GRAPH = {
    "frame": "wired",
    "nodes": [{"kind": "effect", "file": "palette"}],
    "wires": [
        {"from": "shape", "to": "scene.geometry"},
        {"from": "hands", "to": "scene.geometry"},      # the hands inside the scene, with depth
        {"from": "scene", "to": "palette.image"},       # one effect after the scene
        {"from": "palette", "to": "output.all.image"},
        {"from": "hands", "to": "hands.layer.hands"},
        {"from": "hands.layer", "to": "output.all.guide"},   # the guide over it, clean
    ],
}
STILL = {f"rot.rate.{p}": 0.0 for p in ("XY", "XZ", "YZ", "XW", "YW", "ZW")}
BASE = {
    **STILL, "view.rotate": False, "view.shape": 3,           # the tesseract, standing still
    "view.lines": True, "view.points": True, "view.faces": False, "view.bright": 1.4,
    "view.depth4": 2.6, "view.instances": 1, "view.inst_fit": False, "view.inst_motion": 0,
    "camera.zoom": 1.0, "camera.yaw": 0.5, "camera.pitch": 0.35,
    "camera.pan.x": 0.0, "camera.pan.y": 0.0,
    "ghost.on": True, "ghost.alpha": 1.0, "ghost.guide": 1, "ghost.style": 0,
    "fx.on": True, "dream.on": False,
    "fx.palette.on": True, "fx.palette.mix": 1.0, "fx.palette.mode": 0,
    "fx.palette.hue_from": 170.0, "fx.palette.hue_to": 300.0, "fx.palette.sat_from": 0.55,
}
VARIANTS = [
    ("1 one shape", "659: the shape, hands in the scene, one effect", {}),
    ("2 field", "659 again: seven copies, Fit off (the offset's path)",
     {"view.instances": 7, "view.inst_layout": 1, "camera.zoom": 0.55}),
    ("3 fit", "659 again: nine copies, Fit on (no offset there, row 851)",
     {"view.instances": 9, "view.inst_layout": 0, "view.inst_fit": True}),
]


def script(d, panel):
    lp = panel.library.loaded_patch
    lib = panel.library
    seed_dir = lib.home / "loadable"
    seed_dir.mkdir(parents=True, exist_ok=True)
    report = {}
    for name, note, extra in VARIANTS:
        seed = seed_dir / "wc-seed.json"
        seed.write_text(json.dumps({"schema": "hyperspace.preset/7", "name": "wc-seed",
                                    "note": note, "graph": GRAPH,
                                    "values": {**BASE, **extra}, "routes": [], "macros": {}}))
        missing = lp.load("wc-seed")
        yield from d.wait(10)
        path = lp.save_as(f"{FOLDER}/{name}")
        seed.unlink()
        report[name] = {"missing": missing, "path": str(path)}
        yield from d.wait(150)                  # screenshots of this one
    lp.load(f"{FOLDER}/1 one shape")
    panel.reg["ui.page"].set(PAGE_KEYS.index("camera"))
    yield from d.wait(20)
    yield from d.click("world.reset", frames=10)
    yield from d.park()
    yield from d.wait(40)
    dst = OUT / "patches"
    dst.mkdir(parents=True, exist_ok=True)
    for r in report.values():
        shutil.copy(r["path"], dst / Path(r["path"]).name)
    (OUT / "report.json").write_text(json.dumps(report, indent=1))
