"""tempo.py and lfo.py take a clock, a registry and a router as arguments
and import nothing from the host — the same rule the hands package keeps
(test_hands_boundary.py), for the same reason: the boundary erodes one
convenient import at a time.
"""

import pytest
from walls import family, imports, inside, module_of, shown

# the leaves a standalone module may import: the LFOs are a modulator bank
# (plan 31 B), and modbank.py keeps the same rule (test_modbank.py)
LEAVES = {"tempo": set(), "lfo": {"modbank"}}
STEMS = {f: stem for stem in LEAVES for f in family(stem)}


@pytest.mark.parametrize("path", STEMS, ids=shown)
def test_the_clock_and_the_lfos_import_nothing_from_the_host(path):
    """Each may import its own split and its leaves: tempo can't reach lfo, nor lfo tempo."""
    stem = STEMS[path]
    allowed = {module_of(f)[0] for f in family(stem)} | LEAVES[stem]
    for mod, level in imports(path):
        if level:
            where = inside(path, mod, level)
            assert where and where[0] in allowed, \
                f"{shown(path)} imports from the package: {'.' * level}{mod}"
        else:
            assert not mod.startswith("hyperspace"), f"{shown(path)} imports {mod}"


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
