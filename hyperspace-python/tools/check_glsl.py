#!/usr/bin/env python3
"""Compile the face shaders with the Khronos reference compiler.

The app's GL driver is the only compiler the tests use, and a driver is
lenient in its own ways: Mesa accepts things Apple's GL 4.1 core compiler
rejects (an int where a float is wanted, say). This assembles each
fragment shader that reads patterns.glsl exactly as render.py does — the
face program, the seed (the faces' effects' first pass) and the pattern
tile — writes it to a temporary `.frag` and runs `glslangValidator` on it,
which holds `#version 330` to the letter. It prints each verdict and exits
non-zero on any error.

    uv run python tools/check_glsl.py

Needs `glslangValidator` on the PATH (Debian/Ubuntu: glslang-tools).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hyperspace import render as R

PROGRAMS = {
    "face": (R.FACE_FS_HEAD, R.FACE_FS_TAIL),
    "seed": (R.SEED_FS_HEAD, R.SEED_FS_TAIL),
    "tile": (R.TILE_FS_HEAD, R.SEED_FS_TAIL),
}


def main() -> int:
    exe = shutil.which("glslangValidator")
    if exe is None:
        print("glslangValidator not found on the PATH")
        return 2
    src = R.PATTERNS_GLSL.read_text()
    bad = 0
    with tempfile.TemporaryDirectory() as tmp:
        for name, (head, tail) in PROGRAMS.items():
            path = Path(tmp) / f"{name}.frag"
            # glslang wants the version line first, as every driver does
            path.write_text(R._face_fragment(head, src, tail).lstrip())
            out = subprocess.run([exe, str(path)], capture_output=True, text=True, check=False)
            text = (out.stdout + out.stderr).strip()
            ok = out.returncode == 0
            bad += not ok
            print(f"{name:5s} {'ok' if ok else 'FAILED'}")
            if not ok or "WARNING" in text:
                print("   " + text.replace("\n", "\n   "))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
