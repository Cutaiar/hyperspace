"""The face patterns' eight inputs and twelve modes, as data — the one
place their names and meanings live.

`shaders/patterns.glsl` paints the faces, reading eight inputs, `u_mod[8]`
— the registry's `pattern.mod.0`–`.7` (0–2.6, 1.0 the un-driven look).
Each input means the same kind of change in every mode (plan 22 B1), so a
route that feels right on one pattern means the same thing on the next:

  0 SCALE   1 GLOW   2 WARP   3 SPEED   4 COLOUR   5 SHARP   6 HUE   7 SPREAD

The order is for the factory routes (`routing.legacy6_routes`), which put
the analyzer's lane i on input i — SUB BASS MIDB MID UPR AIR, slow and
heavy to fast and bright: the sub swells the scale, the kick flashes the
glow, the low mids bend the lines, the mids drive the speed, the upper
mids flare the colour and the air sharpens the edges. HUE and SPREAD, 6
and 7, are left for an LFO, a macro or a knob: a hue that follows a band
flickers, and how far the faces drift apart is a scene's choice. Each
meaning stands on its own whatever drives it.

`params` takes the mode list and each input's label and tip from here, and
the panel what each input does in the mode on screen (`effect`). The
shader keeps its own copy of the convention — named accessors
(`m_scale()` …) and a header comment — which the tests hold to this table.
Nothing here imports anything, so any layer may read it.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Input:
    name: str        # the label: SCALE
    meaning: str     # what it does in every mode, 0 … 1 … 2.6
    why: str         # why it sits at this index


@dataclass(frozen=True)
class Mode:
    name: str                       # the menu's name: RINGS
    about: str                      # one line: what the pattern is
    does: tuple[str, ...]           # per input, what it does here; "" = ignores it


INPUTS: tuple[Input, ...] = (
    Input("SCALE", "How big the elements are: 0 small and many, 1 as designed, "
                   "2.6 big and few.",
          "lane 0, SUB: the slowest, heaviest band swells the whole picture."),
    Input("GLOW", "How brightly the pattern burns: 0 dim, 1 as designed, "
                  "2.6 bright and white-hot.",
          "lane 1, BASS: the kick flashes the faces."),
    Input("WARP", "How far the pattern's lines bend and wave: 0 straight, 1 as designed, "
                  "2.6 heavily warped.",
          "lane 2, MIDB: the low mids' body bends the geometry."),
    Input("SPEED", "How fast the pattern moves: 0 frozen, 1 as designed, 2.6 times as fast. "
                   "The clock is integrated, so a moving SPEED never jumps.",
          "lane 3, MID: the busiest band keeps the motion flowing with the music."),
    Input("COLOUR", "How much colour: 0 grey, 1 as designed, 2.6 more hues and "
                    "stronger colour.",
          "lane 4, UPR: the snare and the presence flare the colour."),
    Input("SHARP", "How hard the edges are: 0 soft and broad, 1 as designed, "
                   "2.6 thin and crisp.",
          "lane 5, AIR: bright sound, sharp image — the hats crisp the lines."),
    Input("HUE", "Turns the palette round the colour wheel, half a turn per unit: "
                 "0 half a turn back, 1 as designed, 2.6 four fifths of a turn on.",
          "free for an LFO: a band on hue flickers, a slow cycle does not."),
    Input("SPREAD", "How differently each face plays: 0 every face in unison, "
                    "1 as designed, 2.6 each face its own phase and colour.",
          "free for a macro or a knob: unison or scattered is a scene's choice."),
)

N_INPUTS = len(INPUTS)
INDEX = {i.name: k for k, i in enumerate(INPUTS)}
SCALE, GLOW, WARP, SPEED, COLOUR, SHARP, HUE, SPREAD = range(N_INPUTS)

# what finish() in patterns.glsl does to every mode alike: GLOW, COLOUR's
# grey end and HUE read the same on each, and SPEED is the clock
_GLOW = "the whole pattern's light"
_SPEED = "how fast {}"
_HUE = "turns the palette"

MODES: tuple[Mode, ...] = (
    Mode("FLAT", "A plain white fill — no pattern runs, so it reads none of the inputs.",
         ("",) * N_INPUTS),
    Mode("RINGS", "Two ring sources beating; the hue rides the ring phase.",
         ("ring spacing", _GLOW, "bends the rings", _SPEED.format("the rings travel"),
          "hue range along the rings", "ring edges: soft to thin", _HUE,
          "each face its own beat")),
    Mode("PLAID", "Two coloured wave systems crossing: warm and cool add, cancel to dark.",
         ("stripe spacing", _GLOW, "bends stripes (above 1)",
          _SPEED.format("the waves cross"), "hues drift across it",
          "stripes: soft to thin", _HUE, "faces drift apart above 1")),
    Mode("MOIRE", "Near-frequency stripe fields beating; a slow teal–magenta duotone.",
         ("stripe and beat size", _GLOW, "bends stripes (above 1)",
          _SPEED.format("the beat sways"), "hues band across stripes",
          "stripes: soft to thin", _HUE, "each face its own angle")),
    Mode("BLOOM", "A ring of seven petals turning, its hue round the wheel.",
         ("ring size and width", _GLOW, "bends the ring (above 1)",
          _SPEED.format("the petals turn"), "petals turn apart in hue",
          "petals and ring: soft to thin", _HUE,
          "each face its own tint")),
    Mode("CAUSTIC", "Deep water: dark blue troughs, cyan-white filaments where swells cross.",
         ("swell size", _GLOW, "bends the swells", _SPEED.format("the water moves"),
          "the swells take more hues", "filaments: broad to thin", _HUE,
          "each face its own swell")),
    Mode("HEX", "A honeycomb lattice, every cell firing on its own phase.",
         ("cell size", _GLOW, "bends the lattice (above 1)",
          _SPEED.format("the cells fire"), "how many hues the cells take",
          "cell edges and flashes", _HUE, "each face its own firing")),
    Mode("SPIRAL", "Galaxy arms winding out of a hot core.",
         ("looser arms, bigger core", _GLOW, "bends the arms",
          _SPEED.format("the arms wind"), "hue range out along the arms",
          "arms: broad to thin", _HUE, "each face its own turn")),
    Mode("CELLS", "Living voronoi: bright membranes between drifting nuclei.",
         ("cell size", _GLOW, "bends the cells", _SPEED.format("the nuclei drift"),
          "how many hues the cells take", "membranes: soft to thin", _HUE,
          "each face its own drift")),
    Mode("PLASMA", "The classic folded sine field on the full hue wheel.",
         ("fold size", _GLOW, "bends the folds", _SPEED.format("the field flows"),
          "how far the hues run", "folds: soft to thin bands", _HUE,
          "each face its own swirl")),
    Mode("WEAVE", "Warp and weft ribbons interlaced over and under on a checker.",
         ("thread size", _GLOW, "ribbon wobble, then bends",
          _SPEED.format("the ribbons breathe"), "each thread its own hue",
          "ribbons: wide to thin", _HUE,
          "faces drift apart above 1")),
    Mode("EMBER", "Coals breathing under ash: rising noise, white-hot where it peaks.",
         ("coal size", _GLOW, "bends the coals", _SPEED.format("the heat rises"),
          "ash and flame part in hue", "broad glow to hot points", _HUE,
          "each face its own coals")),
)

NAMES = [m.name for m in MODES]


def effect(mode: int, k: int) -> str:
    """What input `k` does in mode `mode`, in a few words; "" when it does nothing."""
    return MODES[mode].does[k]


def ignores(mode: int) -> list[int]:
    """The inputs mode `mode` does not read."""
    return [k for k, d in enumerate(MODES[mode].does) if not d]


def label(k: int) -> str:
    """Input `k`'s registry label: "Pattern scale"."""
    return f"Pattern {INPUTS[k].name.lower()}"


def tip(k: int) -> str:
    """Input `k`'s tooltip: its name, what it means in every mode, and how to drive it."""
    i = INPUTS[k]
    return (f"{i.name} — {i.meaning} The same kind of change in every pattern "
            f"(hyperspace/patterns.py says what it does in each). Route a band, an LFO "
            f"or a knob here; 1.0 is the un-driven look.")
