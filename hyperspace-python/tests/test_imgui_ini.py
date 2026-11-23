"""A test's imgui keeps no ini file (conftest `_no_imgui_ini`).

imgui's default is `imgui.ini` in the working directory: a test run, the
real app or `tools/app_driver.py` left the panel's layout there, and the
next run's test rig loaded it — `test_dial`'s unplugged pad failed on a
local tree and never on CI's fresh checkout (the kit's RETRO row 70)."""

import pytest

imgui = pytest.importorskip("imgui_bundle").imgui

PLANTED = "[Window][Probe]\nPos=300,300\nSize=40,40\nCollapsed=1\n"


def _frame():
    io = imgui.get_io()
    io.display_size = imgui.ImVec2(640, 480)
    io.backend_flags |= imgui.BackendFlags_.renderer_has_textures
    imgui.new_frame()
    imgui.set_next_window_pos(imgui.ImVec2(10, 10), imgui.Cond_.first_use_ever)
    open_ = imgui.begin("Probe")[0]
    pos = imgui.get_window_pos()
    imgui.end()
    imgui.render()
    return open_, (pos.x, pos.y)


def test_a_planted_ini_is_neither_read_nor_written(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ini = tmp_path / "imgui.ini"
    ini.write_text(PLANTED)
    ctx = imgui.create_context()
    try:
        assert imgui.get_io().get_ini_filename() == ""
        open_, pos = _frame()
        assert open_ and pos == (10.0, 10.0)      # not collapsed, not at 300, 300
        _frame()
    finally:
        imgui.destroy_context(ctx)                # where imgui saves its ini
    assert ini.read_text() == PLANTED
    assert [p.name for p in tmp_path.iterdir()] == ["imgui.ini"]


def test_with_no_ini_none_is_written(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ctx = imgui.create_context()
    try:
        _frame()
    finally:
        imgui.destroy_context(ctx)
    assert list(tmp_path.iterdir()) == []
