# dkit's fonts

The kit sets its text in **Inter**, the family the panel sets its own words
in (`hyperspace/fonts`, Inter 4.1), so a section drawn on the kit and one
drawn by `ui.py` are one typeface. The React oracle renders in the same
Inter (`@fontsource-variable/inter`, `prototypes/dashboard/src/index.css`),
so the comparison against Chromium is the same typeface too.

The oracle's file is a *variable* font in *woff2*, which Dear ImGui's font
loader (FreeType in imgui_bundle; stb_truetype upstream) cannot read: it has
no woff2 decompressor and cannot select an instance along a variation axis.
So these are static instances cut from that exact file by
`dev/build_fonts.py`:

| File | Weight | Source | Licence |
| --- | --- | --- | --- |
| `Inter-Regular.ttf` | wght 400 | instanced from `@fontsource-variable/inter` `files/inter-latin-wght-normal.woff2` (Inter 4.001, the text optical size - the cut the panel's own Inter is) | SIL OFL 1.1, `Inter-OFL.txt` |
| `Inter-Medium.ttf` | wght 500 | the same | the same |
| `Inter-SemiBold.ttf` | wght 600 | the same | the same |
| `*-tnum.ttf` | the same | the same, tabular figures frozen into the cmap | the same |

**These are modified**, unlike the panel's own faces in `hyperspace/fonts/`,
which are each a family's unmodified release. Beyond instancing,
`build_fonts.py` changes three tables and nothing else: `hhea` and the
`OS/2` typo metrics get a one-em line box (0.8 / -0.2 em), so that ImGui's
font size is the CSS px; the `cmap` gains a Private Use codepoint for every
glyph a default substitution can produce (and, in `-tnum`, points the
figures at their tabular forms); and `head` keeps the source's timestamp.
What the files no longer say - the real ascender and descender, the
kerning, the substitution rules and the exact advances - goes to
`metrics.json`, which `draw.py` reads; the build checks `draw.shape`
against HarfBuzz on every face before it finishes.

Inter is OFL 1.1 with **no Reserved Font Name** declared, so derived
instances may keep the family name. Latin subset only; symbols the subset
lacks (arrows, the command key) come from the panel's DejaVu, merged behind
every face as `ui.py` does.

Geist, the family shadcn ships with and the kit was first measured in, was
replaced by Inter here (RETRO rows 90-94).
