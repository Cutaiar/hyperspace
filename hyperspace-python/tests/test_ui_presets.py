"""Plan 14 WP4: the PRESETS page for a party — headless imgui over the
controls rig (tests/test_ui_shell.py), on a fresh home, which opens the
factory party show (decision 22).

Top to bottom: the show's name on its own line, never covered; show ▾ ·
save · save as · new; "starts on ▾", saved when set; eight preset buttons
carrying their presets' names; the preset strip; "more" folded. The dirty
dots compare against the loaded preset or show, so a factory load is clean.
"""

import json

from imgui_bundle import imgui
from test_ui_routing import _drawn
from test_ui_shell import _page_scroll, frame, rig  # noqa: F401 — the fixture

from hyperspace import ui_presets
from hyperspace.library import Library
from hyperspace.ui import PAGES


def _overlap(a, b) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _rects(panel):
    return dict(ui_presets._state(panel)["rects"])


def test_the_shows_name_is_never_covered(rig, tmp_path):  # noqa: F811
    """The layout bug the owner hit: the startup combo drew over the
    project's name, so only "de" of "default" showed. The name has its line
    to itself; no widget on the page overlaps it; it fits the line — a long
    name too."""
    panel, lib = rig.panel, rig.lib
    for name in (None, "FRIDAY NIGHT AT THE WAREHOUSE"):
        if name:
            ui_presets._project_save_as(panel, name)
        frame(panel, "presets")
        frame(panel)
        rects = _rects(panel)
        shown = rects["show.name"]
        assert shown[2] - shown[0] >= imgui.calc_text_size("x").x * len(lib.project.name) * 0.5
        line = rects["show.line"]
        assert line[0] <= shown[0] and shown[2] <= line[2], "the name runs off its line"
        others = {k: r for k, r in rects.items()
                  if k not in ("show.name", "show.line", "show.dot")}
        assert {"show.menu", "show.save", "show.save_as", "show.new", "starts_on",
                "starts_on.label", "preset.0", "preset.7"} <= set(others)
        hit = [k for k, r in others.items() if _overlap(shown, r)]
        assert hit == [], f"covering the show's name: {hit}"
        # and the widgets below never overlap one another
        keys = sorted(others)
        for i, a in enumerate(keys):
            for b in keys[i + 1:]:
                assert not _overlap(others[a], others[b]), (a, b)


def test_the_preset_buttons_carry_their_presets_names(rig):  # noqa: F811
    panel, lib = rig.panel, rig.lib
    lib.load("presets", "FACES")
    frame(panel, "presets")
    frame(panel)
    labels = ui_presets._state(panel)["bank_labels"]
    assert labels == ["F1  TUMBLE", "F2  FACES", "F3  FIELD", "F4  WAKE", "F5  TRIP",
                      "F6  —", "F7  —", "F8  —"][: len(labels)] and len(labels) == 8
    assert lib.project.active == 1                          # FACES, lit
    rects = _rects(panel)
    assert rects["preset.2"][1] > rects["preset.0"][1]       # F3 F4 under F1 F2
    assert rects["preset.2"][0] == rects["preset.0"][0] < rects["preset.1"][0]


def test_a_long_preset_name_is_elided_to_its_button(rig):  # noqa: F811
    panel, lib = rig.panel, rig.lib
    lib.project.bank[5] = "A PRESET NAME FAR TOO LONG FOR ONE BUTTON"
    frame(panel, "presets")
    frame(panel)
    label = ui_presets._state(panel)["bank_labels"][5]
    assert label.startswith("F6  A PRESET NAME") and label.endswith("…")


def test_the_dots_are_clean_after_a_factory_load(rig):  # noqa: F811
    """Plan 14 §1: right after a factory preset loaded, the rail lit dots on
    VIEW / CAMERA / LOOKBACK / FX / LFO (they compared against fresh
    defaults) and the footer said the factory show was unsaved. Now every
    dot compares against the loaded preset or show."""
    panel, lib, reg = rig.panel, rig.lib, rig.reg
    for name in ("TRIP", "WAKE", "BIG BLUE WAVE"):
        lib.load("presets", name)
        groups = [g for _k, _l, grp in PAGES
                  for g in ((grp,) if isinstance(grp, str) else (grp or ()))]
        lit = [g for g in groups if ui_presets.dirty(panel, g)]
        assert lit == [], f"{name}: dirty dots on {lit}"
        assert not lib.project.is_dirty(), "the factory show is not unsaved"
    frame(panel, "presets")
    reg["view.bright"].set_value(reg["view.bright"].value + 1.0)   # an edit: the dot comes back
    assert ui_presets.dirty(panel, "view") and ui_presets.dirty(panel, "presets")
    assert not lib.project.is_dirty()                     # a performance move: the preset's
    reg["master.gain"].set(reg["master.gain"].value + 1.0)  # a session move: the show's
    assert ui_presets.dirty(panel, "master") and lib.project.is_dirty()


def test_starts_on_is_labelled_and_saved_when_set(rig, tmp_path, monkeypatch):  # noqa: F811
    panel, lib = rig.panel, rig.lib
    texts, previews = _drawn(monkeypatch)
    frame(panel, "presets")
    frame(panel)
    assert "STARTS ON" in texts and "TUMBLE" in previews
    ui_presets.set_starts_on(panel, "WAKE")
    path = tmp_path / "projects" / "party.hyp.json"          # the factory show: your copy
    doc = json.loads(path.read_text())
    assert doc["startup"] == "WAKE" and doc["name"] == "party"
    assert not lib.project.is_dirty() and lib.project.path == path
    assert (tmp_path / "last_show").read_text() == "party\n"
    again = Library(tmp_path, period=0.0)
    assert again.project.name == "party" and again.project.startup == "WAKE"


def test_the_page_speaks_one_word_per_thing(rig, monkeypatch):  # noqa: F811
    """Plan 14 §3: show, preset, starts on, module preset, factory — the
    page never says project or startup."""
    panel = rig.panel
    texts, previews = _drawn(monkeypatch)
    frame(panel, "presets")
    frame(panel)
    words = " ".join(texts + previews).lower()
    assert "show" in words and "starts on" in words and "factory" in words
    assert "project" not in words and "startup" not in words
    # "more" is folded: no module strip drawn until it is opened
    assert not any(t.startswith("view ") for t in texts)


def test_more_opened_holds_a_strip_per_module_and_still_fits(rig, monkeypatch):  # noqa: F811
    real = imgui.collapsing_header
    monkeypatch.setattr(imgui, "collapsing_header",
                        lambda label, *a: (real(label, *a), True)[1] if "more" in label
                        else real(label, *a))
    texts, _ = _drawn(monkeypatch)
    frame(rig.panel, "presets")
    frame(rig.panel)
    groups = ui_presets.groups(rig.panel)
    assert {"view", "camera", "fx", "band"} <= set(groups)
    assert all(f"{g:<8s}" in texts for g in groups)
    assert _page_scroll(rig, monkeypatch)["presets"] == 0
