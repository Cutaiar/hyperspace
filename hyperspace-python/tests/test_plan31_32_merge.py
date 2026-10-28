"""Plans 31 and 32 together (register row 340, hand check 317): one
schema ladder, ``/4`` = ``/3`` + media (D1), read whole by a load. Row 394
(the owner, 2026-10-25): a save is always ``/6``, carrying both families
and the bins — D1's lowest-schema save and D3's "left out at its default"
are gone with it.

`fixtures/merge-31-32/` holds what each branch's own code wrote for the
same state, before the merge: ``v3-only.json`` by plan 31's head
(615d4fb, `test_plan31_wiring.make_app`, two steps on and an envelope's
attack moved), ``media-free.json`` by plan 32's head (3ad7842,
`test_presets.boot`, one view value moved)."""

from dataclasses import replace
from pathlib import Path

import pytest
from test_plan31_wiring import make_app
from test_presets import boot

from hyperspace import preset
from hyperspace.library import LibraryError

FIXTURES = Path(__file__).parent / "fixtures" / "merge-31-32"
V2, V3, V4 = "hyperspace.preset/2", "hyperspace.preset/3", "hyperspace.preset/4"
V6 = "hyperspace.preset/7"   # (plan 36 T3: the save schema, named for the row it pinned)
CLIP = "shared:loops/tunnel.mp4"


@pytest.fixture()
def app(tmp_path):
    return make_app(tmp_path)


def _backdrop(app, c: str | None) -> None:
    """Channel `c` under the scene (None: none) as the GRAPH page lands it
    (plan 33 T7: the wire `media.<c> → backdrop.image`, where
    `backdrop.channel` was)."""
    from hyperspace import graph as G

    gs = app.presets.graph
    if c is None:
        gs.land(None)
        return
    old = {"wires": [{"from": "frame", "to": "fx.image"},
                     {"from": f"media.{c}", "to": "backdrop.image"}]}
    # (plan 36 T3: a GRAPH landing is a wired frame — the old words wired)
    from hyperspace import graphmigrate as M

    section = M.wired_section(M.renamed(old), G.read_graph(old))
    gs.land(G.read_graph(section), section)


def _backdrop_of(app) -> str | None:
    from hyperspace import graph as G

    spec = app.presets.graph.spec
    return G.channel_into(spec.all_wires(), "backdrop.image") if spec is not None else None


def _pattern_and_bin(app) -> None:
    reg = app.reg
    reg["seq.1.1"].set(True)
    reg["seq.3.5"].set(True)
    reg["env.1.attack"].set(0.4)
    reg.media.assign("a", 0, CLIP)
    _backdrop(app, "a")


def test_the_ladder_is_one_list():
    assert preset.VERSIONS == (2, 3, 4, 5, 6, 7, 8)   # (plan 35: /6; plan 36 T3: /7; plan 40 T2: /8)
    assert (preset.SCHEMA, preset.SCHEMA_V3, preset.MEDIA_SCHEMA) == (V2, V3, V4)
    assert preset.WIRED_SCHEMA == V6
    # the factory generator's rule (`generated`): /3 for a pattern, else /2
    assert preset.factory_schema({"values": {"seq.1.1": True}}) == V3
    assert preset.factory_schema({"lfos": [1, 2]}) == V3
    assert preset.factory_schema({"values": {"view.media_alpha": 1.0}}) == V2


def test_a_pattern_and_a_bin_save_as_6_and_round_trip(app):
    reg = app.reg
    _pattern_and_bin(app)
    doc = app.presets.document("both")
    assert doc["schema"] == V6 and next(iter(doc)) == "schema"
    # every value of both families, and the bins — and no retired id (the
    # channel under the scene is the graph's wire)
    from hyperspace import graphmigrate as M

    assert doc["values"] == reg.snapshot(part="performance")
    assert not [k for k in doc["values"] if M.retired(k)]
    assert doc[preset.MEDIA_KEY] == {"channels": {"a": [CLIP]}}
    app.presets.save_as("both")
    # undo it all, then load
    reg["seq.1.1"].set(False)
    reg["seq.3.5"].set(False)
    reg["env.1.attack"].set(0.01)
    reg.media.assign("a", 0, None)
    _backdrop(app, None)
    assert app.presets.load("both") == []
    assert reg["seq.1.1"].value is True and reg["seq.3.5"].value is True
    assert reg["env.1.attack"].value == pytest.approx(0.4)
    assert _backdrop_of(app) == "a"
    assert reg.media.channels["a"].bin[0] == CLIP
    # and stable through a load (once a load has read the file's integers
    # back as floats, as every preset since plan 13 does)
    again = app.presets.save_as("both").read_bytes()
    assert app.presets.load("both") == []
    assert app.presets.save_as("both").read_bytes() == again


def test_an_older_build_refuses_the_combined_save(app):
    """A build before plan 35 (2 … 5), one of plan 31 alone (2, 3) and one
    from before both (2,) refuse the `/6` whole rather than strip half of it
    on a re-save (row 394: both Macs are on the newest build, so none
    should be asked to)."""
    _pattern_and_bin(app)
    app.presets.save_as("both")
    lib = app.lib
    assert lib.read("presets", "both")["schema"] == V6
    kinds = lib._kinds
    try:
        for versions in ((2, 3, 4, 5), (2, 3), (2,)):
            kinds["presets"] = replace(kinds["presets"], versions=versions)
            with pytest.raises(LibraryError, match="is not a hyperspace.preset"):
                lib.read("presets", "both")
    finally:
        kinds["presets"] = replace(kinds["presets"], versions=preset.VERSIONS)


def test_what_each_branch_wrote_loads_and_saves_as_6(app, tmp_path):
    """The files plan 31's head (a pattern, `/3`) and plan 32's (one view
    value, `/2`) wrote for the same state load with what they said and save
    `/6` with it."""
    import json

    doc = json.loads((FIXTURES / "v3-only.json").read_text())
    assert doc["schema"] == V3
    assert app.presets.load_doc(doc) == []
    reg = app.reg
    assert reg["seq.1.1"].value is True and reg["seq.3.5"].value is True
    assert reg["env.1.attack"].value == pytest.approx(0.4)
    out = app.presets.document("pattern")
    assert out["schema"] == V6 and out["values"]["seq.1.1"] is True
    r = boot(tmp_path / "plain")
    doc = json.loads((FIXTURES / "media-free.json").read_text())
    assert doc["schema"] == V2
    assert r.presets.load_doc(doc) == []
    assert r.reg["view.bright"].value == pytest.approx(1.5)
    out = r.presets.document("plain")
    assert out["schema"] == V6 and out["values"]["view.bright"] == pytest.approx(1.5)


def test_a_media_value_is_saved_wherever_it_stands(app):
    """Row 394: a media value is written whatever it is — at the group's
    default module's value or at the build default — so a reload lands it
    rather than the module's (D3's "left out at its default" was the
    lowest-schema save's)."""
    reg, lib = app.reg, app.lib
    build = reg["view.media_alpha"].value
    reg["view.media_alpha"].set(0.5)
    lib.save_as("view", "default")                 # the view group's default module
    assert lib.defaults("view")["view.media_alpha"] == pytest.approx(0.5)
    doc = app.presets.document("x")
    assert doc["schema"] == V6 and doc["values"]["view.media_alpha"] == pytest.approx(0.5)
    reg["view.media_alpha"].set(build)
    doc = app.presets.document("x")
    assert doc["schema"] == V6 and doc["values"]["view.media_alpha"] == build
    app.presets.save_as("x")
    reg["view.media_alpha"].set(0.5)
    assert app.presets.load("x") == []
    assert reg["view.media_alpha"].value == build
