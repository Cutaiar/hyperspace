"""One real launch over an owner-like home, driving plan 19 WP4 through
the library while the app runs (the real-launch check of WP4's PR).

  uv run python tools/trash_launch.py

A fresh temp folder is built by `tests/conftest.py::build_owner_home` and
`HYPERSPACE_HOME` points at it before anything reads it, so this never
touches ~/Hyperspace. Then `hyperspace.app.main` runs for
`HYPERSPACE_FRAMES=120` frames — it opens the render and control windows
briefly — with `app.frame` wrapped: a few frames in, through the running
app's own Library, it hides a factory preset (TRIP), renames NIGHT TWO to
SUNRISE, deletes NIGHT THREE and restores it from the trash. Afterwards it
prints whether any frame raised (or returned False), whether `stall.log`
gained anything, and the home's tree with what each file became.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

HOME = Path(tempfile.mkdtemp(prefix="hyperspace-trash-launch-")) / "home"
os.environ["HYPERSPACE_HOME"] = str(HOME)
os.environ["HYPERSPACE_FRAMES"] = "120"
ROOT = Path(__file__).resolve().parents[1]
for extra in (ROOT, ROOT / "tests"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from conftest import build_owner_home

from hyperspace import app


def listing(home: Path) -> dict[str, str]:
    return {p.relative_to(home).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()[:12]
            for p in sorted(home.rglob("*")) if p.is_file()}


def main() -> int:
    build_owner_home(HOME)
    before = listing(HOME)
    stall = (HOME / "stall.log").read_bytes()
    three = (HOME / "presets" / "night-three.json").read_bytes()
    steps = {10: "hide", 20: "rename", 30: "delete", 40: "restore"}
    seen = {"n": 0, "false": 0, "raised": [], "said": [], "errors": set()}
    real = app.frame

    def frame(h, now, dt, fps):
        seen["n"] += 1
        step = steps.get(seen["n"])
        lib = h.panel.library
        try:
            if step == "hide":
                lib.hide("presets", "TRIP")
            elif step == "rename":
                lib.rename("presets", "NIGHT TWO", "SUNRISE")
            elif step == "delete":
                lib.delete("presets", "NIGHT THREE")
            elif step == "restore":
                (item,) = [t for t in lib.trash() if t.name == "NIGHT THREE"]
                lib.restore_trash(item)
        except Exception as e:  # noqa: BLE001 — reported, never swallowed silently
            seen["raised"].append(f"{step}: {type(e).__name__}: {e}")
        if step:
            seen["said"].append(f"frame {seen['n']:>3} {step:<8} status: {lib.status!r}"
                                + (f"  warning: {lib.warning!r}" if lib.warning else ""))
        try:
            ok = real(h, now, dt, fps)
        except Exception as e:
            seen["raised"].append(f"frame {seen['n']}: {type(e).__name__}: {e}")
            raise
        if ok is False:
            seen["false"] += 1
        err = h.reloader.runtime_error or h.reloader.error
        if err:
            seen["errors"].add(str(err)[:200])
        return ok

    app.frame = frame
    try:
        app.main()
    finally:
        app.frame = real
    after = listing(HOME)
    print(f"home: {HOME}")
    print(f"frames run: {seen['n']}   frames that returned False: {seen['false']}   "
          f"raised: {seen['raised'] or 'none'}   reloader errors: {sorted(seen['errors']) or 'none'}")
    for line in seen["said"]:
        print("  " + line)
    print(f"stall.log unchanged: {(HOME / 'stall.log').read_bytes() == stall}")
    print("the home afterwards (path, sha256[:12], vs before):")
    for path in sorted(before.keys() | after.keys()):
        b, a = before.get(path), after.get(path)
        what = ("same" if a == b else "NEW" if b is None else "GONE" if a is None else "changed")
        print(f"  {path:<52} {a or '-':<12} {what}")
    hidden = json.loads((HOME / "hidden.json").read_text())
    mine = json.loads((HOME / "projects" / "mine.hyp.json").read_text())
    checks = {
        "hidden.json names party-trip": hidden["presets"] == ["party-trip"],
        "night-two.json gone, sunrise.json there": (
            not (HOME / "presets" / "night-two.json").exists()
            and json.loads((HOME / "presets" / "sunrise.json").read_text())["name"] == "SUNRISE"),
        "night-three.json restored byte for byte": (
            (HOME / "presets" / "night-three.json").read_bytes() == three),
        "mine names SUNRISE on F2": mine["bank"][1] == "SUNRISE",
        "trash holds night-two and mine's old show, not night-three": (
            {p.name.split(".")[0] for p in (HOME / "trash" / "presets").iterdir()}
            == {"night-one", "night-two"}
            and [p.name.split(".")[0] for p in (HOME / "trash" / "projects").iterdir()]
            == ["mine"]),
        "party.hyp.json untouched": (after["projects/party.hyp.json"]
                                     == before["projects/party.hyp.json"]),
    }
    for what, ok in checks.items():
        print(f"  {'ok  ' if ok else 'FAIL'} {what}")
    return 0 if all(checks.values()) and not seen["raised"] and not seen["false"] else 1


if __name__ == "__main__":
    sys.exit(main())
