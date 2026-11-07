"""The geometry the desk and pad diagrams share (ui_desk.py, ui_pad.py): where
they sit from the control window's edges, their padding, their header's line,
their glyphs' size.

A leaf, importing nothing of the app's: ui_pad reads these at import, and it
is imported from inside `ui`, which ui_desk imports, so read from ui_desk they
were half-made whenever ui_desk was imported first (row 808; the hot-reload
test's report imports every module cold, and CI went red on the ones whose
order put ui_desk first). ui_desk and ui_pad import them from here."""

EDGE = 12.0                # from the control window's edges, the panel and the sheet
PAD = 8.0
HEAD_H = 26.0              # the header's line: the layer, the loadable patch, the chip
GLYPH_PX = 10.0            # the glyphs' type size
GAP = EDGE                 # from the cheat sheet
