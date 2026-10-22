"""tempo.py and lfo.py take a clock, a registry and a router as arguments
and import nothing from the host — the same rule the hands package keeps
(test_hands_boundary.py), for the same reason: the boundary erodes one
convenient import at a time.
"""

import ast
from pathlib import Path

import pytest

PKG = Path(__file__).resolve().parents[1] / "hyperspace"
STANDALONE = ("tempo.py", "lfo.py")
# the leaves a standalone module may import: the LFOs are a modulator bank
# (plan 31 B), and modbank.py keeps the same rule (test_modbank.py)
LEAVES = {"lfo.py": {"modbank"}}


def _imports(path: Path):
    """(module, level) for every import in the file."""
    out = []
    for n in ast.walk(ast.parse(path.read_text())):
        if isinstance(n, ast.ImportFrom):
            out.append((n.module or "", n.level))
        elif isinstance(n, ast.Import):
            out += [(a.name, 0) for a in n.names]
    return out


@pytest.mark.parametrize("name", STANDALONE)
def test_the_clock_and_the_lfos_import_nothing_from_the_host(name):
    for mod, level in _imports(PKG / name):
        if level == 1 and mod in LEAVES.get(name, ()):
            continue
        assert not level, f"{name} imports from the package: {'.' * level}{mod}"
        assert not mod.startswith("hyperspace"), f"{name} imports {mod}"


def test_they_run_with_no_host_at_all():
    """No registry, no router: a clock and four LFOs still produce values."""
    from hyperspace.lfo import LFOs
    from hyperspace.tempo import Clock

    clock = Clock(now=lambda: 0.0)
    lfos = LFOs(seed=1)
    lfos[1].sync = 3                     # one bar
    for k in range(10):
        out = lfos.step(1 / 60, k / 60, clock)
    assert len(out) == 4 and all(0.0 <= u <= 1.0 for u in out)

    class Router:                        # the whole host contract for output
        def __init__(self):
            self.labels, self.rests = {}, {}   # routing.Router has both from __init__

        def feed(self, scheme, values):
            self.fed = (scheme, list(values))

    r = Router()
    lfos.publish(r)
    assert r.fed[0] == "lfo" and len(r.fed[1]) == 4
    assert r.labels["lfo"] == ["LFO 1", "LFO 2", "LFO 3", "LFO 4"]
    assert r.rests["lfo"] == [0.5] * 4
