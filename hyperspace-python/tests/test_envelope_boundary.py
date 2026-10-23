"""envelope.py takes a clock and a registry as arguments and imports
nothing from the host but the leaf `modbank` — the rule tempo.py and lfo.py
keep (test_lfo_boundary.py): the boundary erodes one convenient import at a
time. The envelopes are a modulator bank (plan 31 W1), and modbank.py keeps
the same rule (test_modbank.py).
"""

import ast
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "hyperspace"
LEAVES = {"modbank"}       # the leaves envelope.py may import


def test_the_envelope_imports_nothing_from_the_host():
    for n in ast.walk(ast.parse((PKG / "envelope.py").read_text())):
        if isinstance(n, ast.ImportFrom):
            if n.level == 1 and n.module in LEAVES:
                continue
            assert not n.level, f"envelope.py imports from the package: {n.module}"
            assert not (n.module or "").startswith("hyperspace"), n.module
        elif isinstance(n, ast.Import):
            assert not any(a.name.startswith("hyperspace") for a in n.names)


def test_it_runs_with_no_host_at_all():
    """No registry, no router, no clock: a fired envelope still rises and falls."""
    from hyperspace.envelope import REST, Envelope

    e = Envelope()
    assert e.step(0.0) == REST == 0.0
    e.fire(at=0.0, gate=0.1)
    out = [e.step(k / 60) for k in range(120)]
    assert max(out) > 0.9 and out[-1] == 0.0 and all(0.0 <= u <= 1.0 for u in out)

    class Clock:                          # the whole host contract for beats mode
        bpm = 120.0

    e = Envelope(sync=1)
    e.fire(at=0.0)
    assert e.step(0.5, Clock()) > 0.0
