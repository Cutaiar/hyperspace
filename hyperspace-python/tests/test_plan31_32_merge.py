"""Plans 31 and 32 together (register row 340, hand check 317): the one
schema ladder, ``/4`` = ``/3`` + media (D1), and "at its default" read as
the library's for both families (D3).

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
    section = {"wires": [{"from": "frame", "to": "fx.image"},
                         {"from": f"media.{c}", "to": "backdrop.image"}]}
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
    assert preset.VERSIONS == (2, 3, 4, 5)
    assert (preset.SCHEMA, preset.SCHEMA_V3, preset.MEDIA_SCHEMA) == (V2, V3, V4)
    # the document-only rule (factory presets, `generated`) knows /4 too
    assert preset.schema_of({"values": {"seq.1.1": True}}) == V3
    assert preset.schema_of({"values": {"seq.1.1": True},
                             "routes": [{"source": "lfo:0", "target": "media.a.pos"}]}) == V4
    assert preset.schema_of({"lfos": [1, 2], "media": {"channels": {"a": [CLIP]}}}) == V4
    assert preset.schema_of({"values": {"view.media_alpha": 1.0}}) == V2


def test_a_pattern_and_a_bin_save_as_4_and_round_trip(app):
    reg = app.reg
    _pattern_and_bin(app)
    doc = app.presets.document("both")
    assert doc["schema"] == V4 == preset.schema_of(doc) and next(iter(doc)) == "schema"
    # /4 carries every value of both families, and the bins
    snap = reg.snapshot(part="performance")
    assert {k for k in doc["values"] if k.startswith(("env.", "seq."))} == {
        k for k in snap if k.startswith(("env.", "seq."))}
    # (plan 33 T7: and the two retired channel choices, written back as a
    # build from before plan 33 reads them)
    assert {k for k in doc["values"] if preset.is_media_id(k)} == {
        k for k in snap if preset.is_media_id(k)} | {"view.media", "backdrop.channel"}
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
    assert _backdrop_of(app) == "a" and doc["values"]["backdrop.channel"] == 1
    assert reg.media.channels["a"].bin[0] == CLIP
    assert app.presets.document("both") == doc
    # and stable through a load (once a load has read the file's integers
    # back as floats, as every preset since plan 13 does)
    again = app.presets.save_as("both").read_bytes()
    assert app.presets.load("both") == []
    assert app.presets.save_as("both").read_bytes() == again


def test_an_older_build_refuses_the_combined_4(app):
    """A build of plan 31 alone (2, 3) and one from before both (2,) refuse
    the file whole rather than strip half of it on a re-save."""
    _pattern_and_bin(app)
    app.presets.save_as("both")
    lib = app.lib
    assert lib.read("presets", "both")["schema"] == V4
    kinds = lib._kinds
    try:
        for versions in ((2, 3), (2,)):
            kinds["presets"] = replace(kinds["presets"], versions=versions)
            with pytest.raises(LibraryError, match="is not a hyperspace.preset"):
                lib.read("presets", "both")
    finally:
        kinds["presets"] = replace(kinds["presets"], versions=preset.VERSIONS)


# the lines plan 32 changes in every preset (its row 337's rough edge): the
# six `view.bmp_*` values gone, its two effect files' values added
BMP, LATER_EFFECTS = '  "view.bmp_', ('  "fx.displace.', '  "fx.blend.')


def test_a_3_only_and_a_media_free_preset_are_what_each_branch_wrote(app, tmp_path):
    # a pattern, no media: /3 with no media value or key — plan 31's file,
    # but for plan 32's own change to every preset
    app.reg["seq.1.1"].set(True)
    app.reg["seq.3.5"].set(True)
    app.reg["env.1.attack"].set(0.4)
    doc = app.presets.document("pattern")
    assert doc["schema"] == V3 and preset.MEDIA_KEY not in doc
    assert not any(preset.is_media_id(k) for k in doc["values"])
    want = "".join(line for line in (FIXTURES / "v3-only.json").read_text().splitlines(True)
                   if not line.startswith(BMP))
    got = preset.dumps(doc).splitlines(True)
    assert any(line.startswith(LATER_EFFECTS) for line in got)
    assert "".join(line for line in got if not line.startswith(LATER_EFFECTS)) == want
    # no pattern, no media: /2, byte for byte plan 32's file
    r = boot(tmp_path / "plain")
    r.reg["view.bright"].set(1.5)
    doc = r.presets.document("plain")
    assert doc["schema"] == V2
    assert preset.dumps(doc) == (FIXTURES / "media-free.json").read_text()


def test_media_at_the_librarys_default_is_untouched(app):
    """D3: a media value counts as untouched when it is what a load lands
    for it missing — the group's default module over the build values —
    not when it equals the build default."""
    reg, lib = app.reg, app.lib
    build = reg["view.media_alpha"].value
    reg["view.media_alpha"].set(0.5)
    lib.save_as("view", "default")                 # the view group's default module
    assert lib.defaults("view")["view.media_alpha"] == pytest.approx(0.5)
    # at the module's value: no media, so /2 and the value left out
    doc = app.presets.document("x")
    assert doc["schema"] == V2 and "view.media_alpha" not in doc["values"]
    # at the build default, which is off the module's: /4, kept, and a
    # reload lands it rather than the module's 0.5
    reg["view.media_alpha"].set(build)
    doc = app.presets.document("x")
    assert doc["schema"] == V4 and doc["values"]["view.media_alpha"] == build
    app.presets.save_as("x")
    reg["view.media_alpha"].set(0.5)
    assert app.presets.load("x") == []
    assert reg["view.media_alpha"].value == build
