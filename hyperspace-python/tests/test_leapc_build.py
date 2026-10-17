"""The vendored leapc_cffi build finds whichever Gemini's LeapC is installed.

vendor/leapc-cffi/setup.py is upstream's, patched to look the library up by
pattern (highest libLeapC.<N>.dylib, then libLeapC.dylib) instead of the
hard-coded libLeapC.5.dylib. It only builds when run as the setup script, so
importing it by path here runs nothing and needs no SDK.
"""

import importlib.util
from pathlib import Path

import pytest

SETUP = Path(__file__).resolve().parents[1] / "vendor" / "leapc-cffi" / "setup.py"


@pytest.fixture(scope="module")
def setup_py():
    pytest.importorskip("setuptools")  # setup.py imports it; here only through torch
    spec = importlib.util.spec_from_file_location("leapc_cffi_setup", SETUP)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def _no_override(monkeypatch):
    monkeypatch.delenv("LEAPC_LIB_OVERRIDE", raising=False)


def _touch(directory: Path, *names: str) -> None:
    for name in names:
        (directory / name).write_bytes(b"")


def test_gemini_6_picks_the_versioned_library(setup_py, tmp_path):
    _touch(tmp_path, "libLeapC.6.dylib", "libLeapC.dylib")
    found = setup_py.find_leapc_library(str(tmp_path), "Darwin")
    assert Path(found).name == "libLeapC.6.dylib"


def test_highest_version_wins(setup_py, tmp_path):
    _touch(tmp_path, "libLeapC.5.dylib", "libLeapC.6.dylib", "libLeapC.10.dylib")
    found = setup_py.find_leapc_library(str(tmp_path), "Darwin")
    assert Path(found).name == "libLeapC.10.dylib"


def test_gemini_5_only(setup_py, tmp_path):
    _touch(tmp_path, "libLeapC.5.dylib")
    found = setup_py.find_leapc_library(str(tmp_path), "Darwin")
    assert Path(found).name == "libLeapC.5.dylib"


def test_only_the_unversioned_library(setup_py, tmp_path):
    _touch(tmp_path, "libLeapC.dylib")
    found = setup_py.find_leapc_library(str(tmp_path), "Darwin")
    assert Path(found).name == "libLeapC.dylib"


def test_none_found_says_where_and_what(setup_py, tmp_path):
    with pytest.raises(setup_py.LeapCNotFoundError) as caught:
        setup_py.find_leapc_library(str(tmp_path), "Darwin")
    message = str(caught.value)
    assert str(tmp_path) in message
    assert "libLeapC.<N>.dylib" in message and "libLeapC.dylib" in message
    for var in ("LEAPSDK_INSTALL_LOCATION", "LEAPC_LIB_OVERRIDE"):
        assert var in message


def test_override_wins(setup_py, tmp_path, monkeypatch):
    _touch(tmp_path, "libLeapC.6.dylib")
    elsewhere = tmp_path / "custom"
    elsewhere.mkdir()
    _touch(elsewhere, "libLeapC.5.dylib")
    monkeypatch.setenv("LEAPC_LIB_OVERRIDE", str(elsewhere / "libLeapC.5.dylib"))
    found = setup_py.find_leapc_library(str(tmp_path), "Darwin")
    assert found == str(elsewhere / "libLeapC.5.dylib")


def test_missing_override_raises(setup_py, tmp_path, monkeypatch):
    _touch(tmp_path, "libLeapC.6.dylib")
    monkeypatch.setenv("LEAPC_LIB_OVERRIDE", str(tmp_path / "nope.dylib"))
    with pytest.raises(setup_py.LeapCNotFoundError, match="LEAPC_LIB_OVERRIDE"):
        setup_py.find_leapc_library(str(tmp_path), "Darwin")


def test_linux_and_windows_names(setup_py, tmp_path):
    _touch(tmp_path, "libLeapC.so", "libLeapC.so.5", "libLeapC.so.6")
    assert Path(setup_py.find_leapc_library(str(tmp_path), "Linux")).name == "libLeapC.so.6"
    win = tmp_path / "win"
    win.mkdir()
    _touch(win, "LeapC.dll")
    assert Path(setup_py.find_leapc_library(str(win), "Windows")).name == "LeapC.dll"


def test_unversioned_symlink_is_staged_under_its_real_name(setup_py, tmp_path):
    # Hand Tracking 6.2: libLeapC.dylib -> libLeapC.6.dylib, whose install name
    # (@rpath/libLeapC.6.dylib) is what the compiled module asks for
    _touch(tmp_path, "libLeapC.6.dylib")
    (tmp_path / "libLeapC.dylib").symlink_to("libLeapC.6.dylib")
    staged = setup_py.staged_library_name(str(tmp_path / "libLeapC.dylib"), "Darwin")
    assert staged == "libLeapC.6.dylib"
    assert setup_py.staged_library_name(str(tmp_path / "libLeapC.6.dylib"), "Darwin") == (
        "libLeapC.6.dylib"
    )


def test_cleanup_removes_stale_build_and_staged_libraries(setup_py, tmp_path, monkeypatch):
    # A stale in-tree build/ would keep cffi from relinking after an upgrade
    here = tmp_path / "pkg"
    resource = here / "src" / "leapc_cffi"
    stale_build = here / "build" / "lib" / "leapc_cffi"
    resource.mkdir(parents=True)
    stale_build.mkdir(parents=True)
    _touch(stale_build, "libLeapC.6.dylib", "_leapc_cffi.abi3.so")
    _touch(resource, "__init__.py", "libLeapC.6.dylib")
    monkeypatch.setattr(setup_py, "_HERE", str(here))
    monkeypatch.setattr(setup_py, "_RESOURCE_DIRECTORY", str(resource))
    setup_py._remove_staged_libraries()
    assert not (here / "build").exists()
    assert sorted(p.name for p in resource.iterdir()) == ["__init__.py"]
