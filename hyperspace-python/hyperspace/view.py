"""The view — the live object the view, rotation and camera params write.

`ViewState` mirrors the reference's S object (its render-relevant fields)
and is the thing `Renderer.draw` reads; `integrate` is the one direct
writer of `ang` (ARCHITECTURE §3.2, "object writer"). It lives here, apart
from render.py, so that the registry, the library and every test that
wants the plain dataclass can have it without importing moderngl (audit
V3). render.py re-exports it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .geometry import RATE

N_MOD = 8   # pattern.mod.* inputs the face shader reads as u_mod[N_MOD]
RED = (1.0, 43 / 255, 43 / 255)   # the points' colour, and the panel's one accent (ui.RED)


@dataclass
class ViewState:
    """Mirror of the reference's S object (render-relevant fields)."""

    shape: int = 3
    speed: float = 0.30
    depth4: float = 2.6
    bright: float = 1.0
    points: bool = True
    lines: bool = True
    playing: bool = True
    planes: list[bool] = field(default_factory=lambda: [False, False, True, True, False, False])
    ang: list[float] = field(default_factory=lambda: [0.0] * 6)
    yaw: float = 0.0
    pitch: float = 0.0
    faces: bool = False          # translucent face fills under the wireframe
    cut_through: bool = True     # overlay only: fills lower the window's alpha (render.py)
    zoom: float = 1.0            # camera magnification about the view centre
    pan: list[float] = field(default_factory=lambda: [0.0, 0.0])  # logical px
    instances: int = 1           # synchronized copies in a centred grid; 0 draws nothing
    inst_motion: int = 0         # grid motion: 0 still, 1 orbit, 2 wave, 3 ripple
    inst_amp: float = 0.25       # motion amplitude, fraction of a grid cell
    inst_rate: float = 1.0       # motion angular rate, rad/s
    pattern: int = 0             # face pattern mode (0 = flat fill)
    pattern_mix: float = 1.0     # flat ↔ pattern blend
    bmp_file: str = ""           # bitmap layer over the face pattern, "" = none
    bmp_alpha: float = 1.0       # bitmap opacity fader
    bmp_scale: float = 0.9       # bitmap width, face-UV units (face spans 1.0)
    bmp_mode: int = 0            # bitmap path: 0 still, 1 orbit, 2 fig-8, 3 sway
    bmp_amp: float = 0.15        # path amplitude about the face centre, UV units
    bmp_rate: float = 1.0        # path angular rate, rad/s
    # modulation targets (params.py rot.rate.* / pattern.mod.*): per-plane
    # rate multipliers and the face patterns' inputs — 1.0 is the undriven
    # look; an audio lane routed to them (routing.py) is what the reference
    # called PLANEDRIVE and u_bands (here the u_mod[8] uniform)
    rate: list[float] = field(default_factory=lambda: [1.0] * 6)
    pattern_mod: list[float] = field(default_factory=lambda: [1.0] * N_MOD)

    def integrate(self, dt: float) -> None:
        """The frame() angle update: ang[p] += dt·speed·RATE[p]·rate[p]."""
        if not self.playing:
            return
        for p in range(6):
            if self.planes[p]:
                self.ang[p] += dt * self.speed * RATE[p] * self.rate[p]
