# Review — 39-T5 (GRAPH and the pages), PR #267

**Task quality: Approved** (minors folded in before merge).

Sound: changes confined to `graphview.py` and tests (`ui_graph.py`,
`COLOURS`, `summary`, `graph.py` untouched); the picker — `matte`/`cut`
under a new **masks ▸**, `segment` under a new **media ▸** (the channels
stay under **pictures ▸**; W6's "MEDIA" read literally; one word in
`PICKER_GROUP` folds it back — row 4ta for the owner at AJ.1); the
cut-out starter wires exactly W6's four wires, never refuses, lays left
to right from the click, names what it replaced (`_was_into`, shared with
the scene chain — plan 36's follow-up) and says the scene's geometry is
left unwired on a blank preset (WYSIWYG: a fifth wire would be a
fill-in); a cable whose maker makes a mask is MASK-typed (purple into a
red port) — not a regression (a mask into a picture port was refused
before plan 39; the IMAGE-keyed menu actions already refused promoted
cables in `_cable_ends`); `segment.N`'s pins drawn once per instance,
tested; the words only on stand-ins; the `/7` round trip; `edges` on the
FX page; +20 tests.

Minors: `returns()` keys the backward-wire rule on `c.type == IMAGE` (a
promoted cable into a taken-back port no longer a return — fixed to the
taker's port); a test whose docstring did not match its section; a row
for insert-effect on a promoted mask (both `_cable_ends` and ui_graph's
`c.type` checks). Seam: `build()` is edited by both plan 39 and plan 37.
