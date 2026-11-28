"""The macro candidates (test fixtures in
tests/fixtures/macro-candidates/; the owner
has them in his library) load cleanly through the real road — copied into
a library's loadable/, then `LoadedPatch.load` — with no note, no dropped row,
every subscriber on a real param or a route the file carries. Whether
the macros are any good is the
owner's listening rig, not a test's."""

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from conftest import boot_home

from hyperspace import routing
from hyperspace.bands import CEIL
from hyperspace.fx import FxState, retaper_of
from hyperspace.params import Kind

CANDIDATES = Path(__file__).resolve().parent / "fixtures" / "macro-candidates"
FILES = sorted(CANDIDATES.glob("*.json"))
# The effects' speed and amount params are on tapers, and the
# candidates' base subscribers on them were migrated end for end
# (tools/retaper_routes.py: each `from` / `to` lands the real value it did).
# A macro's throw is linear in norm, so between its ends it now runs the
# taper's curve: a macro resting at noon no longer lands the scene's own
# value on such a param, and two macros sharing one (macro-breakdown-drop's
# 1 and 3 on `fx.warp.amount`) no longer agree there — the owner re-sets
# those by ear. The checks below that
# assume the old agreement skip these params; test_retaper.py holds the ends.
_FILES_OF_FX = FxState().files


def _read(path: Path) -> dict:
    """The candidate as a load reads it: through the one ladder
    (`graphmigrate.forward`): its Hue cycle retired, Hue turn and
    its bands' field nodes, as in the owner's library on load."""
    from hyperspace import graphmigrate
    specs = {n: (s.order, s.mix) for n, s in _FILES_OF_FX.items()}
    return graphmigrate.forward(json.loads(path.read_text()), specs).doc


def _not_hue(notes) -> list:
    """`notes` less what the retirement of Hue cycle says."""
    return [n for n in notes if "Hue cycle" not in n]


def _retapered(pid: str) -> bool:
    return retaper_of(pid, _FILES_OF_FX) is not None
# the sets meant to be played all at once: no param has two macros' bases
# (macro-intensity and macro-breakdown-drop compare versions of one idea,
# so their macros share bases on purpose — the last one turned wins)
WHOLE_SETS = ("macro-performance", "macro-streams")

@pytest.fixture()
def rig(tmp_path):
    home = tmp_path / "home"
    (home / "loadable").mkdir(parents=True)
    for f in FILES:
        shutil.copyfile(f, home / "loadable" / f.name)
    return boot_home(home)


def test_there_are_candidates():
    assert {p.stem for p in FILES} >= {"macro-performance", "macro-streams",
                                       "macro-intensity", "macro-breakdown-drop"}


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_each_candidate_loads_with_no_note_and_keeps_every_row(rig, path):
    doc = _read(path)
    assert _not_hue(rig.loaded_patch.load(path.stem)) == []
    assert _not_hue(rig.loaded_patch.notes) == [] and rig.loaded_patch.desk_notes == []
    table = rig.router.table
    assert table.dropped == []
    assert [b.to_json() for b in table.routes()] == doc["routes"]
    assert table.macros_doc() == doc["macros"]          # no subscriber dropped
    # the file is one scene: landing the macros at their resting positions
    # moves no base off the file's own value
    for pid, v in doc["values"].items():
        p = rig.reg[pid]
        if p.kind is Kind.CONTINUOUS and not _retapered(pid):     # (see _retapered)
            assert p.norm == pytest.approx(p._norm_of(v), abs=1e-4), (path.stem, pid)


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_every_subscriber_names_a_real_param_or_a_route_of_its_file(rig, path):
    """A base subscriber names a continuous patch param a loadable patch may
    set (`routing.base_refusal`); a depth subscriber names an enabled route
    the file carries, onto a modulatable param. Every macro has a label and
    the file's note says what each one does."""
    doc = _read(path)
    rig.loaded_patch.load(path.stem)
    reg = rig.reg
    routes = {(r["source"], r["target"]) for r in doc["routes"] if r.get("enabled", True)}
    seen: dict[str, list[str]] = {}
    for mid, m in routing.macros_of(doc["macros"]).items():
        assert routing.is_macro(mid) and reg.get(mid) is not None, mid
        assert m.label and m.label in doc["note"], (path.stem, mid)
        assert m.subs, (path.stem, mid)
        for s in m.subs:
            if s.base is not None:
                p = reg.get(s.base)
                assert p is not None and p.kind is Kind.CONTINUOUS, s.base
                assert routing.base_refusal(s.base, reg) is None, s.base
                assert 0.0 <= s.lo <= 1.0 and 0.0 <= s.hi <= 1.0, s     # fader norms
                seen.setdefault(s.base, []).append(mid)
            else:
                assert s.depth in routes, (path.stem, mid, s.depth)
                target = reg.get(s.depth[1])
                assert target is not None and target.modulatable, s.depth
    if path.stem in WHOLE_SETS:
        assert {pid: ms for pid, ms in seen.items() if len(ms) > 1} == {}


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_turning_a_macro_moves_its_bases_and_scales_its_routes(rig, path):
    """The wiring, not the taste: each macro at either end puts each base
    subscriber at its `from` / `to` and each depth subscriber's route
    pushes by its depth times the range's end."""
    doc = _read(path)
    rig.loaded_patch.load(path.stem)
    reg, router = rig.reg, rig.router
    loud = SimpleNamespace(lanes=np.full(6, 0.5 * CEIL))     # every band at half the ceiling
    router.feed("lfo", np.ones(4))                          # every LFO at the top of its swing

    def offset(target: str) -> float:
        router.modulate(loud)
        o = reg[target]._mod
        reg.apply()
        return o

    for mid, m in routing.macros_of(doc["macros"]).items():
        pushed = {}
        for end in (0.0, 1.0):
            reg[mid].set(end)
            router.follow_macros()
            for s in m.subs:
                if s.base is not None:
                    if _retapered(s.base):          # (see _retapered: shared bases disagree)
                        continue
                    assert reg[s.base].norm == pytest.approx(s.at(end), abs=1e-4), (mid, s)
                else:
                    pushed[(s.depth, end)] = offset(s.depth[1])
        for s in m.subs:
            if s.depth is not None:
                at0, at1 = pushed[(s.depth, 0.0)], pushed[(s.depth, 1.0)]
                # the route's push is in the ratio of the range's ends
                assert at1 * s.lo == pytest.approx(at0 * s.hi, abs=1e-9), (mid, s)
                assert at1 != 0.0 or s.hi == 0.0, (mid, s)
        reg[mid].set(doc["values"][mid])
        router.follow_macros()
