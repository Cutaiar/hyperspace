"""Run a patch set's README copy command (`loadable/<set>/README.md`) the
way the owner would: in `hyperspace-python/`, on a Mac whose
`~/Hyperspace/config.toml` names a library, or names none.

The command is `tools/copy_patches.py`, which reads the library as desktop
startup does (`app.main`: `config.load()["library"]["path"]`) and refuses
what is no library. Here `HYPERSPACE_HOME` is a folder under `tmp_path` and
`uv run python` is this interpreter, so a run touches neither the real home
nor the network.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]      # hyperspace-python/, where the README runs
UV_PYTHON = "uv run python"


def command(readme: Path) -> str:
    """The README's one ```bash block, with `uv run python` as this interpreter."""
    blocks = re.findall(r"```bash\n(.*?)```", readme.read_text(), re.DOTALL)
    assert len(blocks) == 1, f"{readme}: one bash block, got {len(blocks)}"
    assert blocks[0].count(UV_PYTHON) == 1, blocks[0]
    return blocks[0].replace(UV_PYTHON, shlex.quote(sys.executable))


def run(readme: Path, machine: Path, library_path: Path | str | None) -> subprocess.CompletedProcess:
    """Run the README's command with `machine` as `~/Hyperspace`, whose
    config.toml names `library_path` (None: no `[library] path`)."""
    machine.mkdir(parents=True, exist_ok=True)
    toml = "" if library_path is None else f'[library]\npath = "{library_path}"\n'
    (machine / "config.toml").write_text(toml)
    env = {**os.environ, "HYPERSPACE_HOME": str(machine)}
    return subprocess.run(["bash", "-c", command(readme)], cwd=ROOT, env=env,
                          capture_output=True, text=True, timeout=120, check=False)
