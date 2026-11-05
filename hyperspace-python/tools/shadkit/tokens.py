"""shadcn design tokens, as data.

The light palette is Tailwind's neutral ramp exactly (verified against the
computed styles of prototypes/dashboard), plus one red. Every value is
achromatic except `destructive`, so there is no colour-management risk in
moving them to ImGui: an sRGB byte triple is the whole story.

Colours are "#rrggbb" or "#rrggbbaa". `rgba()` returns the 0..1 float tuple
ImGui wants, extending the parser idea in hyperspace/ui_pad_lab.py:30-52.
"""

from __future__ import annotations

# --- light ----------------------------------------------------------------
LIGHT = {
    "background": "#ffffff",
    "foreground": "#0a0a0a",
    "card": "#ffffff",
    "primary": "#171717",
    "primary-foreground": "#fafafa",
    "secondary": "#f5f5f5",
    "secondary-foreground": "#171717",
    "muted": "#f5f5f5",
    "muted-foreground": "#737373",
    "accent": "#f5f5f5",
    "border": "#e5e5e5",
    "input": "#e5e5e5",
    "ring": "#a1a1a1",
    "destructive": "#e7000b",
    "sidebar": "#fafafa",
    "transparent": "#00000000",
}

# --- dark (the one Hyperspace will actually wear) -------------------------
DARK = {
    "background": "#0a0a0a",
    "foreground": "#fafafa",
    "card": "#171717",
    "primary": "#e5e5e5",
    "primary-foreground": "#171717",
    "secondary": "#262626",
    "secondary-foreground": "#fafafa",
    "muted": "#262626",
    "muted-foreground": "#a1a1a1",
    "accent": "#404040",
    "border": "#ffffff1a",
    "input": "#ffffff26",
    "ring": "#737373",
    "destructive": "#ff6467",
    "sidebar": "#171717",
    "transparent": "#00000000",
}

# --radius: 0.625rem = 10px, and the scale shadcn derives from it.
RADIUS = 10.0
RADII = {
    "sm": RADIUS - 4,   # 6
    "md": RADIUS - 2,   # 8
    "lg": RADIUS,       # 10
    "xl": RADIUS + 4,   # 14  (cards)
    "4xl": RADIUS + 16,  # 26  (badges; clamps to h/2 on short boxes)
}


def rgba(c: str | tuple, a: float = 1.0, theme: dict | None = None) -> tuple:
    """"#rrggbb" | "#rrggbbaa" | a token name | (r,g,b[,a]) 0-255 -> floats 0-1.

    `a` multiplies whatever alpha the colour already carries, so
    rgba("destructive", 0.10) is Tailwind's `bg-destructive/10`.
    """
    if theme and isinstance(c, str) and c in theme:
        c = theme[c]
    if isinstance(c, (tuple, list)):
        v = [x / 255.0 for x in c]
        if len(v) == 3:
            v.append(1.0)
        return (v[0], v[1], v[2], v[3] * a)
    s = c.lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    r = int(s[0:2], 16) / 255.0
    g = int(s[2:4], 16) / 255.0
    b = int(s[4:6], 16) / 255.0
    al = int(s[6:8], 16) / 255.0 if len(s) == 8 else 1.0
    return (r, g, b, al * a)


# Per-variant chrome for Badge, read off src/components/ui/badge.tsx.
# Every variant carries a 1px border; only `outline` makes it visible.
BADGE = {
    "default": {"fill": ("primary", 1.0), "border": ("transparent", 1.0)},
    "secondary": {"fill": ("secondary", 1.0), "border": ("transparent", 1.0)},
    "destructive": {"fill": ("destructive", 0.10), "border": ("transparent", 1.0)},
    "outline": {"fill": ("transparent", 1.0), "border": ("border", 1.0)},
}
