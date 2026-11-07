"""The audio stack — audio.py, analysis.py, analyzer.py, bands.py and the
tests' offline.py driver — imports nothing from above it: no routing, no
registry, no panel, no render stack, no library, no host (ARCHITECTURE §1,
the Audio source row). The same cheap AST check that keeps the hands
package and the LFOs liftable (test_hands_boundary.py, test_lfo_boundary.py).
"""

import pytest
from walls import family, imports, inside, module_of, shown

FILES = [f for stem in ("audio", "analysis", "analyzer", "bands", "offline") for f in family(stem)]
# the stack may reach only itself, the taper maths and the followers (motion.py)
ALLOWED = {module_of(f)[0] for f in FILES} | {"tapers", "motion"}


@pytest.mark.parametrize("path", FILES, ids=shown)
def test_the_audio_stack_imports_nothing_above_it(path):
    for mod, level in imports(path):
        if level:
            where = inside(path, mod, level)
            assert where and where[0] in ALLOWED, \
                f"{shown(path)} reaches up the stack: {'.' * level}{mod}"
        else:
            assert not mod.startswith("hyperspace"), f"{shown(path)} imports {mod}"


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
