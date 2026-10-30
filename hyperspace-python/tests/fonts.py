"""What a UI test may assume of the type it measures in.

ui.py draws in the Mac's faces (SF Rounded, SF Mono). Off the Mac — the CI
runner — it falls back to DejaVu (`ui._FONT_CANDIDATES`), which is wider:
a line the Mac's panel fits whole is drawn fitted (`ui.fit_text`: its
start and "…"), and a desk glyph with no room on its face is left out
(`ui_desk._text`). A test that holds a line whole, or every glyph drawn,
holds it on the Mac; elsewhere it holds the fitted form.
"""

from __future__ import annotations

import os

from hyperspace import ui

MAC_FONTS = os.path.exists(ui._SF_ROUNDED)


def as_drawn(texts: list[str], s: str) -> str | None:
    """`s` as it was drawn among `texts`: whole; or, off the Mac, its
    fitted start with "…" (`ui.fit_text`). None when it was not drawn."""
    if s in texts:
        return s
    if MAC_FONTS:
        return None
    return next((t for t in texts
                 if len(t) > 1 and t.endswith("…") and s.startswith(t[:-1])), None)
