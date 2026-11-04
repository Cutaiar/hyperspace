"""Which controllers the app knows, and what an entry's ``controller =`` picks.

**One vocabulary for every pad.** A row names a control by what it is on
an Xbox pad — ``pad:A``, ``axis:LT`` — whatever pad is in the hand: the
DualSense's cross is ``pad:A``, its L2 ``axis:LT``, its Create
``pad:VIEW`` (SDL's positional mapping), so a preset made on one pad
plays on the other. `CANON` is that vocabulary as indices into a pad's
button list: the Xbox's raw GLFW indices as they always were
(gamepad.py's map, captured on a Series S), then the controls an Xbox
pad lacks at indices well past anything a GLFW pad reports
(`TOUCH`…`RFN`, from 32), so no raw index ever lands on one.

**A `Model` per kind of pad**: its USB ids, its family, the road that
reads it (``glfw``, ``hid``, ``usb``), what it has (`caps`), what its
controls are called on its own face (`glyphs`: ✕ for ``pad:A`` on a
DualSense) — the on-screen pad draws that, the rows keep the canonical
name — and, for a pad that is less than an Xbox face, which canonical
controls it has at all (`controls`: one Joy-Con has one stick, four
face buttons and no D-pad; None is the whole face). A new controller is
one entry in `MODELS` (and a codec module in `pads/` if no road reads it
yet: `sony` for the DualSense, `nintendo` for the Joy-Con).

**Which pad is which role** (`matches`): an entry's ``controller =``
names a model (``"edge"``), a family (``"sony"``, ``"xbox"``), a USB id
(``"054c:0df2"``) or ``"any"`` (the default: the next free pad, as
before). Entries are served in list order, so two ``any`` pads take the
first two found and ``controller = "edge"`` pins the Edge to its role
whatever else is plugged in.

A leaf: the standard library only (pads/__init__.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---- the canonical buttons: today's Xbox indices, then the extras ----
CANON: dict[str, int] = {
    "A": 0, "B": 1, "X": 3, "Y": 4, "LB": 6, "RB": 7, "VIEW": 10, "MENU": 11,
    "GUIDE": 12, "LSTICK": 13, "RSTICK": 14, "SHARE": 15,
}
TOUCH, LP, RP, LFN, RFN = 32, 33, 34, 35, 36     # a pad without them never sets them
EXTRAS: dict[str, int] = {"TOUCH": TOUCH, "LP": LP, "RP": RP, "LFN": LFN, "RFN": RFN}
CANON.update(EXTRAS)
N_CANON = max(CANON.values()) + 1                # a decoded pad's button list length

# what a pad may have beyond the Xbox's face
CAPS = ("touch", "motion", "back", "fn", "light", "rumble", "triggers", "players", "mic")
OUTPUT_CAPS = frozenset({"light", "rumble", "triggers", "players", "mic"})

SONY_VID = 0x054C
MICROSOFT_VID = 0x045E
NINTENDO_VID = 0x057E
# the families the hid road (pads/hid.py) reads, each through its own codec
HID_FAMILIES = ("sony", "nintendo")


@dataclass(frozen=True)
class Model:
    """One kind of controller. `ids` are the (vendor, product) pairs it
    answers to; `road` the driver that reads it by default; `caps` what
    it has past the Xbox face; `glyphs` canonical control → what its own
    face calls it (anything absent keeps its canonical glyph); `controls`
    the canonical controls it has at all, None for the whole Xbox face."""

    id: str
    name: str
    family: str
    road: str
    ids: tuple[tuple[int, int], ...] = ()
    caps: frozenset[str] = frozenset()
    glyphs: dict[str, str] = field(default_factory=dict)
    controls: frozenset[str] | None = None
    # a pad's own controls (the owner, 2026-11-04, a Joy-Con's): (control,
    # param, op, value) rows that stand in for every table row on that
    # control, whichever table is loaded; and (control, param) table rows
    # this pad does not hear, the control left free for a learned row
    layout: tuple[tuple[str, str, str, float], ...] = ()
    drops: tuple[tuple[str, str], ...] = ()

    def has(self, cap: str) -> bool:
        return cap in self.caps

    def has_control(self, name: str) -> bool:
        """Does this pad have the canonical control `name` (``A``, ``LX``,
        ``UP`` …)? Every pad has the whole Xbox face unless its `controls`
        say less (a single Joy-Con: one stick, no D-pad)."""
        return self.controls is None or name in self.controls

    @property
    def outputs(self) -> frozenset[str]:
        return self.caps & OUTPUT_CAPS


_SONY_GLYPHS = {
    "A": "✕", "B": "○", "X": "□", "Y": "△", "LB": "L1", "RB": "R1",
    "VIEW": "CREATE", "MENU": "OPTIONS", "GUIDE": "PS", "SHARE": "MIC",
    "LSTICK": "L3", "RSTICK": "R3", "LT": "L2", "RT": "R2", "TOUCH": "TOUCH",
    "LP": "L4", "RP": "R4", "LFN": "LFn", "RFN": "RFn",
}
_SONY_OUT = frozenset({"touch", "motion", "light", "rumble", "triggers", "players", "mic"})

# A single Joy-Con (plan 43) is held like a Wii Remote — face up, the stick
# under the thumb, pointing where the hand points — and is first of all
# its six-axis sensor. What it has reads by position: its one stick is the
# left stick (``axis:LX`` / ``LY``, its click ``pad:LSTICK``); the (L)'s
# four arrow buttons are the face by where they sit (↓ ``pad:A``, →
# ``B``, ← ``X``, ↑ ``Y``); its L and ZL ``pad:LB`` and ``axis:LT``, the
# (R)'s R and ZR ``pad:RB`` and ``axis:RT``; SL and SR on the rail are the
# back pair ``pad:LP`` / ``pad:RP`` (as the Edge's paddles); − ``VIEW``,
# + ``MENU``, capture ``SHARE``, HOME ``GUIDE``. No D-pad, no right stick,
# no touchpad. Its outputs: rumble (two bands) and the four player lights
# — no light bar, no trigger resistance, no mic light.
_JOYCON_CAPS = frozenset({"motion", "back", "rumble", "players"})
_JOYCON_COMMON = frozenset({"LX", "LY", "LSTICK", "A", "B", "X", "Y", "LP", "RP"})
# the Joy-Con's own layout (the owner, 2026-11-04): SL / SR the shape in every
# mode, the stick's click the view's reset; − (+ on the R) the totem's reset,
# capture (HOME on the R) the totem on and off. L / ZL (R / ZR) are free
_JOYCON_ROWS = (("LP", "view.shape", "step", -1.0), ("RP", "view.shape", "step", 1.0),
                ("LSTICK", "camera.reset", "fire", 1.0))
_JOYCON_L_LAYOUT = (*_JOYCON_ROWS, ("VIEW", "totem.reset", "fire", 1.0),
                    ("SHARE", "totem.on", "toggle", 1.0))
_JOYCON_R_LAYOUT = (*_JOYCON_ROWS, ("MENU", "totem.reset", "fire", 1.0),
                    ("GUIDE", "totem.on", "toggle", 1.0))
_JOYCON_L_GLYPHS = {
    "A": "↓", "B": "→", "X": "←", "Y": "↑", "LB": "L", "LT": "ZL", "LP": "SL", "RP": "SR",
    "VIEW": "−", "SHARE": "◉", "LSTICK": "L3",
}
# the (R)'s face by position too: its B sits at the bottom (``pad:A``), its
# A at the right (``B``), its Y at the left (``X``), its X at the top (``Y``)
_JOYCON_R_GLYPHS = {
    "A": "B", "B": "A", "X": "Y", "Y": "X",
    "RB": "R", "RT": "ZR", "LP": "SL", "RP": "SR", "MENU": "+", "GUIDE": "HOME",
    "LSTICK": "R3",
}
_PRO_GLYPHS = {"LB": "L", "RB": "R", "LT": "ZL", "RT": "ZR", "VIEW": "−", "MENU": "+",
               "GUIDE": "HOME", "SHARE": "◉", "LSTICK": "L3", "RSTICK": "R3"}

MODELS: dict[str, Model] = {m.id: m for m in (
    Model("xbox", "Xbox pad", "xbox", "glfw", ((MICROSOFT_VID, 0),)),
    Model("x360", "wired Xbox 360 pad", "xbox", "usb"),
    Model("dualsense", "DualSense", "sony", "hid", ((SONY_VID, 0x0CE6),),
          _SONY_OUT, {**_SONY_GLYPHS}),
    Model("edge", "DualSense Edge", "sony", "hid", ((SONY_VID, 0x0DF2),),
          _SONY_OUT | {"back", "fn"}, {**_SONY_GLYPHS}),
    Model("joycon-l", "Joy-Con (L)", "nintendo", "hid", ((NINTENDO_VID, 0x2006),),
          _JOYCON_CAPS, {**_JOYCON_L_GLYPHS},
          _JOYCON_COMMON | {"LB", "LT", "VIEW", "SHARE"},
          _JOYCON_L_LAYOUT, (("LB", "view.shape"),)),
    Model("joycon-r", "Joy-Con (R)", "nintendo", "hid", ((NINTENDO_VID, 0x2007),),
          _JOYCON_CAPS, {**_JOYCON_R_GLYPHS},
          _JOYCON_COMMON | {"RB", "RT", "MENU", "GUIDE"},
          _JOYCON_R_LAYOUT, (("RB", "view.shape"),)),
    # the Pro Controller speaks the Joy-Con's protocol with the whole face
    # (both sticks, a D-pad): the codec reads it; no hand has checked one
    Model("procon", "Pro Controller", "nintendo", "hid", ((NINTENDO_VID, 0x2009),),
          frozenset({"motion", "rumble", "players"}), {**_PRO_GLYPHS}),
    # any other GLFW pad: read with the Xbox map, as every pad was before plan 42
    Model("generic", "gamepad", "generic", "glfw"),
)}
SONY_IDS = {pid for m in MODELS.values() if m.family == "sony" for _, pid in m.ids}
# vendor → the product ids the hid road opens: every model whose road is hid
HID_IDS: dict[int, set[int]] = {}
for _m in MODELS.values():
    if _m.road == "hid":
        for _vid, _pid in _m.ids:
            HID_IDS.setdefault(_vid, set()).add(_pid)

SPECS_WORDS = ("any",) + tuple(MODELS) + tuple(sorted({m.family for m in MODELS.values()}))


def is_model(m) -> bool:
    """Is `m` a `Model` — by its shape, so one made before a hot reload of
    this module (a reader opened earlier holds it) still counts, and a
    test's recording stub does not."""
    return isinstance(getattr(m, "caps", None), frozenset) and isinstance(getattr(m, "id", None), str)


def by_ids(vid: int | None, pid: int | None) -> Model:
    """The model a (vendor, product) pair is: an exact pair first, then a
    vendor-wide entry (product 0: any Microsoft pad is read as an Xbox
    pad), else `generic`."""
    if vid is None:
        return MODELS["generic"]
    for m in MODELS.values():
        if (vid, pid) in m.ids:
            return m
    for m in MODELS.values():
        if (vid, 0) in m.ids:
            return m
    return MODELS["generic"]


def parse_spec(spec) -> str | None:
    """A ``controller =`` value made canonical (lower case, no spaces), or
    None when it names nothing: a word of `SPECS_WORDS`, or ``vvvv:pppp``
    in hex."""
    if not isinstance(spec, str):
        return None
    s = spec.strip().lower()
    if s in SPECS_WORDS:
        return s
    v, colon, p = s.partition(":")
    if colon and len(v) == 4 and len(p) == 4:
        try:
            int(v, 16), int(p, 16)
        except ValueError:
            return None
        return s
    return None


def matches(spec: str | None, model: Model, vid: int | None = None,
            pid: int | None = None) -> bool:
    """May a pad entry with ``controller = spec`` read this controller?
    ``any`` (or none) takes anything; a model id or a family takes its
    own; ``vvvv:pppp`` exactly that USB id."""
    s = parse_spec(spec) if spec else "any"
    if s is None or s == "any":
        return True
    if s == model.id or s == model.family:
        return True
    if ":" in s and vid is not None and pid is not None:
        return s == f"{vid:04x}:{pid:04x}"
    return False


def may_be_hid(spec: str | None) -> bool:
    """Could an entry with ``controller = spec`` take a pad the hid road
    reads (a Sony pad, a Joy-Con)? Else the road need not open — and
    seize — any."""
    s = parse_spec(spec) if spec else "any"
    if s is None:
        return True
    if s == "any" or s in HID_FAMILIES:
        return True
    if s in MODELS:
        return MODELS[s].road == "hid"
    return any(s.startswith(f"{vid:04x}:") for vid in HID_IDS)


may_be_sony = may_be_hid       # plan 42's name, for a module loaded before plan 43


def glfw_ids(guid: str | None) -> tuple[int | None, int | None]:
    """(vendor, product) from a GLFW joystick GUID — SDL's layout: bus
    (LE16) 0000, vendor (LE16) 0000, product (LE16) 0000, version … —
    or (None, None) for a GUID that does not carry them."""
    if not isinstance(guid, str) or len(guid) < 20:
        return None, None
    try:
        vid = int(guid[10:12] + guid[8:10], 16)
        pid = int(guid[18:20] + guid[16:18], 16)
    except ValueError:
        return None, None
    return (vid, pid) if vid else (None, None)


def glyph(model: Model | None, name: str, default: str) -> str:
    """What `model`'s face calls the canonical control `name`."""
    if model is None:
        return default
    return model.glyphs.get(name, default)
