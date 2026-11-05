# dkit's fonts

The diff oracle renders in **Geist**, so the ImGui side has to as well or the
text comparison means nothing.

Geist ships only as a *variable* font in *woff2*. Dear ImGui's stb_truetype
rasterizer can read neither: it has no woff2 decompressor, and it cannot
select an instance along a variation axis. So these are static instances cut
from that exact file.

| File | Weight | Source | Licence |
| --- | --- | --- | --- |
| `Geist-Regular.ttf` | wght 400 | instanced from `@fontsource-variable/geist` `files/geist-latin-wght-normal.woff2` | SIL OFL 1.1, `Geist-OFL.txt` |
| `Geist-Medium.ttf` | wght 500 | the same | the same |
| `Geist-SemiBold.ttf` | wght 600 | the same | the same |

**These are modified**, unlike the panel's own bundled faces in
`hyperspace/fonts/`, which are each a family's unmodified release. They were
produced with `fontTools.varLib.instancer` at a single `wght` and saved as
plain TTF (`flavor = None`, which drops the woff2 container):

```python
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
f = TTFont("geist-latin-wght-normal.woff2")
instancer.instantiateVariableFont(f, {"wght": 500}, inplace=True)
f.flavor = None
f.save("Geist-Medium.ttf")
```

Geist is OFL 1.1 with **no Reserved Font Name** declared, so derived instances
may keep the family name. Latin subset only — this is a measuring rig, not the
panel's font set.
