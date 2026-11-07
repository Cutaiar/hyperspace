"""spec.json against its three consumers.

`spec.json` is the shared contract: the React oracle, the ImGui gallery and
the diff all read it, and they agree only by convention. Nothing tested it
until a Button cell was added and silently went missing from the pixel diff
for three of these reasons at once.

Each failure below is SILENT in the harness, which is why it needs a test
rather than care:

* a kind absent from `contour.KIND` is reclassified as TEXT by diff.py and
  reported in the advisory ink-extent table instead of the chrome one. The
  cell renders on both sides and is never compared.
* a kind with no branch in `Gallery.tsx` falls through to the final `else`,
  which renders a **Badge**. The oracle then draws the wrong component and
  the diff faithfully measures it.
* a kind with no branch in `gallery.py` draws NOTHING on the ImGui side -
  an if/elif chain with no else.

The two source files are read as text on purpose. Importing the Python one
needs a GL context, the TSX one cannot be imported at all, and what is being
checked is which branches EXIST, which is a property of the source.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import contour as C      # noqa: E402

SPEC = json.loads((HERE / "spec.json").read_text())
CELLS = SPEC["cells"]
GALLERY_PY = (HERE / "gallery.py").read_text()
GALLERY_TSX = (HERE.parent.parent.parent
               / "prototypes/dashboard/src/Gallery.tsx").read_text()

KINDS = sorted({c["kind"] for c in CELLS})


def test_every_cell_id_is_unique():
    ids = [c["id"] for c in CELLS]
    dupes = {i for i in ids if ids.count(i) > 1}
    assert not dupes, f"duplicate cell ids: {sorted(dupes)}"


def test_every_chrome_kind_is_known_to_the_diff():
    """Or diff.py silently measures it as text and never compares the box."""
    missing = [k for k in KINDS if k != "text" and k not in C.KIND]
    assert not missing, (
        f"kinds absent from contour.KIND: {missing} - diff.py treats these "
        "as text cells and drops them from the chrome table entirely")


def test_the_diff_does_not_classify_a_chrome_cell_as_text():
    """The same thing stated from the diff's side, over actual cells."""
    astext = sorted({c["kind"] for c in CELLS if c["kind"] not in C.KIND})
    assert astext == ["text"], (
        f"these kinds are measured by ink extent, not by pixel: {astext}")


def test_the_imgui_gallery_draws_every_kind():
    drawn = set(re.findall(r'cell\["kind"\] == "([a-z]+)"', GALLERY_PY))
    missing = [k for k in KINDS if k not in drawn]
    assert not missing, (
        f"gallery.py has no branch for {missing} - the if/elif chain has no "
        "else, so those cells draw nothing on the ImGui side")


def test_the_react_oracle_renders_every_kind():
    """A missing branch here renders a Badge, which is worse than nothing:
    the diff compares the ImGui component against a Badge and reports the
    difference as a fidelity failure of the component."""
    rendered = set(re.findall(r'c\.kind === "([a-z]+)"', GALLERY_TSX))
    # `badge` is the fallback itself, so it needs no explicit branch.
    missing = [k for k in KINDS if k not in rendered and k != "badge"]
    assert not missing, (
        f"Gallery.tsx has no branch for {missing} - these fall through to "
        "the final else, which renders a Badge")


def test_every_cell_fits_the_canvas():
    w, h = SPEC["canvas"]["w"], SPEC["canvas"]["h"]
    out = [(c["id"], c["x"], c["y"], c["w"], c["h"]) for c in CELLS
           if c["x"] < 0 or c["y"] < 0
           or c["x"] + c["w"] > w or c["y"] + c["h"] > h]
    assert not out, f"cells outside the {w}x{h} canvas: {out}"


def test_no_two_cells_overlap():
    """The diff slices a window per cell and pads it by PAD on every side, so
    two cells sharing pixels makes both readings ambiguous."""
    bad = []
    for i, a in enumerate(CELLS):
        for b in CELLS[i + 1:]:
            if (a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"]
                    and a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"]):
                bad.append((a["id"], b["id"]))
    assert not bad, f"overlapping cells: {bad}"
