"""The audio stack — audio.py, analysis.py, analyzer.py, bands.py and the
tests' offline.py driver — imports nothing from above it: no routing, no
registry, no panel, no render stack, no library, no host (ARCHITECTURE §1,
the Audio source row). The same cheap AST check that keeps the hands
package and the LFOs liftable (test_hands_boundary.py, test_lfo_boundary.py).
"""

import ast
from pathlib import Path

import pytest

PKG = Path(__file__).resolve().parents[1] / "hyperspace"
STACK = ("audio.py", "analysis.py", "analyzer.py", "bands.py", "offline.py")
# the stack may reach only itself and the taper maths
ALLOWED = {"audio", "analysis", "analyzer", "bands", "tapers"}


def _imports(path: Path):
    """(module, level) for every import in the file."""
    out = []
    for n in ast.walk(ast.parse(path.read_text())):
        if isinstance(n, ast.ImportFrom):
            out.append((n.module or "", n.level))
        elif isinstance(n, ast.Import):
            out += [(a.name, 0) for a in n.names]
    return out


@pytest.mark.parametrize("name", STACK)
def test_the_audio_stack_imports_nothing_above_it(name):
    for mod, level in _imports(PKG / name):
        if level:
            assert level == 1 and mod.split(".")[0] in ALLOWED, \
                f"{name} reaches up the stack: {'.' * level}{mod}"
        else:
            assert not mod.startswith("hyperspace"), f"{name} imports {mod}"


def test_the_chain_runs_with_no_host_at_all():
    """An analyser and an analyzer over a synthetic tone: lanes in [0, CEIL)."""
    import numpy as np

    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer
    from hyperspace.bands import CEIL

    an = Analyser(48_000.0)
    chain = Analyzer(an)
    t = np.arange(4096) / 48_000.0
    for _ in range(30):
        an.feed(np.sin(2 * np.pi * 110 * t) * 0.5)
        lanes = chain.step(1 / 60)
    assert len(lanes) == 6 and all(0.0 <= x < CEIL for x in lanes)
