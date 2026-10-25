"""The desk coverage report: every preset × every control of the preset layer.

    uv run python tools/desk_coverage.py            # rewrite the committed report
    uv run python tools/desk_coverage.py --check    # exit 1 if it is stale
    uv run python tools/desk_coverage.py --stdout   # print it, write nothing
    uv run python tools/desk_coverage.py --library DIR --stdout
                                                    # a library's presets too (read only)

Plan 24 C3 (decision 19). Each preset is loaded the way the app loads it —
a headless registry, router and `Presets` over a **scratch** library home
made for the run, never the owner's — and each control of the APC40's
preset layer (`layer_controls`) gets one of three words:

  mapped   an enabled preset-layer row is on it, and the preset can show
           its param;
  dark     nothing is on it on the preset layer (or only a disabled row);
  dead     a row is on it, but its param is one the preset cannot show
           (`learn.cannot_show`: a pattern knob with the faces off, an
           effect's knob with that effect off, a dream knob with the
           look-back off, …), or the registry has no such param.

The owner's bar for the authoring pass that follows plan 24 — **at most 4
dark or dead controls on the preset layer** of every preset — is reported
per preset; nothing here remaps a preset to meet it.

The committed report is docs/plans/assets/24-party-fixes/desk-coverage.md;
tests/test_desk_coverage.py regenerates it and fails when the committed
file is stale. The text is deterministic: no dates, no paths, every list
sorted or in the layout's order, so a second run is byte-identical.

`--library DIR` copies DIR's ``presets/`` and ``desk/`` files into the
scratch home first (DIR itself is only read), so the report covers that
library's presets beside the factory's, desk templates included.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from hyperspace import apc40, envelope, learn, lfo, routing, sequencer, tempo
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.control import Control
from hyperspace.fx import FxState
from hyperspace.library import DESK, PRESETS, Library
from hyperspace.lookback import DreamState
from hyperspace.params import build_registry
from hyperspace.preset import Presets
from hyperspace.routing import Binding, Bindings, Router
from hyperspace.view import ViewState

REPORT = ROOT / "docs" / "plans" / "assets" / "24-party-fixes" / "desk-coverage.md"
BAR = 4                     # the owner's bar: at most this many dark or dead
MAPPED, DARK, DEAD = "mapped", "dark", "dead"
MARK = {MAPPED: "●", DARK: "·", DEAD: "✕"}


@dataclass(frozen=True)
class Cell:
    glyph: str
    status: str                 # MAPPED / DARK / DEAD
    target: str = ""            # the row's param ("" when dark)
    why: str = ""               # dead: why the preset cannot show it


@dataclass(frozen=True)
class Row:
    name: str
    cells: tuple[Cell, ...]
    extra: tuple[str, ...]      # "G6·3 → view.speed": rows on controls off the layer

    def count(self, status: str) -> int:
        return sum(c.status == status for c in self.cells)


# ---------------------------------------------------------------- the layer

def layer_controls(table: Bindings | None = None) -> list[apc40.Control]:
    """The controls of the APC40's preset layer, in the layout's order:
    the device knobs D1–D8, the track knobs K1–K8 and the track faders
    S1–S8 — the strips a preset's desk is for (`preset.knob_desk`,
    `track_fader`) — and every other control the factory map gives a
    preset-layer row (`apc40.DEFAULT_MAP`: the cue knob, the plane
    buttons, the grid-motion pads, ▲ ▼, the view reset), less any control
    an invariant row of the session table holds (`table`, the factory one
    when None). A free control no factory row names (clip stops 1–7,
    clip row 2 on the preset layer) is not counted: a row a preset puts
    there is listed beside the table instead."""
    table = Bindings.factory() if table is None else table
    inv = table.invariant_rows()
    rows = [Binding.from_json(d) for d in apc40.DEFAULT_MAP]
    named = {c.glyph for b in rows if b.layer == "preset" for c in apc40.controls(b.source)}
    strips = ({f"cc:*:{n}" for n in apc40.DEVICE_KNOBS}
              | {f"cc:0:{n}" for n in apc40.TRACK_KNOBS}
              | {f"cc:{k}:{apc40.CC_FADER}" for k in apc40.TRACK_FADERS})
    out = []
    for c in apc40.LAYOUT:
        if c.source not in strips and c.glyph not in named:
            continue
        probe = Binding(c.source, "", "abs", layer="preset")
        if table.is_invariant(probe, inv):
            continue
        out.append(c)
    # the three strips first (D, K, S), then the rest in the layout's order
    return sorted(out, key=lambda c: (_STRIPS.index(c.glyph[0]) if is_strip(c) else 3,
                                      _ORDER[c.glyph]))


_STRIPS = "DKS"


def is_strip(c: apc40.Control) -> bool:
    """A device knob, a track knob or a track fader (D1–D8, K1–K8, S1–S8)."""
    return len(c.glyph) == 2 and c.glyph[0] in _STRIPS and c.glyph[1].isdigit()


# ---------------------------------------------------------------- the rig

def boot(home: Path) -> SimpleNamespace:
    """The app's construction order (app.main), headless, on `home` — a
    scratch folder: the library, the registry, the session table (the
    factory's: the home has no bindings.json), the router and `Presets`."""
    chain = Analyzer(Analyser())
    control = Control(chain)
    view = ViewState()
    lib = Library(home, period=0.0)
    reg = build_registry(view, control, SimpleNamespace(chain=chain), lib.project,
                         dream=DreamState(), fx=FxState())
    clock = tempo.Clock(now=lambda: 0.0)
    tempo.register(reg, clock)
    lfo.register(reg, lfo.LFOs(), clock)
    envelope.register(reg, envelope.Envelopes(), clock)      # plan 31: seq-demo's ids
    sequencer.register(reg, sequencer.Sequencer(), clock)
    table = Bindings.load(None, legacy_midi=None)
    routing.register_desk(reg, table)
    lib.attach(reg)
    router = Router(reg, table)
    presets = Presets(lib, reg, router)
    return SimpleNamespace(lib=lib, reg=reg, router=router, presets=presets, table=table)


def coverage_of(rig, name: str, controls: list[apc40.Control]) -> Row:
    """Load preset `name` and read its preset layer against `controls`."""
    rig.presets.load(name)
    reg, table = rig.reg, rig.table
    values = reg.snapshot()
    # (plan 33 T7: whether the faces show a picture is the graph's wire)
    media = learn.faces_media(rig.presets.graph.spec, getattr(reg, "switch_state", None))
    on: dict[str, Binding] = {}
    for b in table.desk():
        if b.enabled:
            for c in apc40.controls(b.source):
                on.setdefault(c.glyph, b)        # the first row a control has wins
    cells = []
    for c in controls:
        b = on.get(c.glyph)
        if b is None:
            cells.append(Cell(c.glyph, DARK))
            continue
        why = "no such param" if reg.get(b.target) is None else learn.cannot_show(
            b.target, values, media)
        cells.append(Cell(c.glyph, DEAD if why else MAPPED, b.target, why or ""))
    glyphs = {c.glyph for c in controls}
    extra = sorted({f"{g} → {b.target}" for g, b in on.items() if g not in glyphs},
                   key=_glyph_order)
    return Row(name, tuple(cells), tuple(extra))


_ORDER = {c.glyph: i for i, c in enumerate(apc40.LAYOUT)}


def _glyph_order(line: str) -> tuple[int, str]:
    return _ORDER.get(line.split(" ", 1)[0], len(_ORDER)), line


def coverage(home: Path, library: Path | None = None) -> tuple[list[apc40.Control], list[Row]]:
    """Every preset the scratch `home` lists (the factory's, and with
    `library` that library's copied in), each a `Row`."""
    if library is not None:
        for group in (PRESETS, DESK):
            src = library / group
            if src.is_dir():
                (home / group).mkdir(parents=True, exist_ok=True)
                for f in sorted(src.glob("*.json")):
                    shutil.copy(f, home / group / f.name)
    rig = boot(home)
    controls = layer_controls(rig.table)
    names = rig.lib.list(PRESETS, hidden=True)
    return controls, [coverage_of(rig, n, controls) for n in names]


# ---------------------------------------------------------------- the text

def report(controls: list[apc40.Control], rows: list[Row],
           source: str = "only the factory presets") -> str:
    """The report as Markdown — the same text for the same presets, every run."""
    n = len(controls)
    out = [
        "# Desk coverage — every preset's preset layer",
        "",
        ("Generated by `tools/desk_coverage.py` (plan 24 C3, decision 19); "
         "`tests/test_desk_coverage.py` fails when this file is stale. Do not edit it by "
         "hand: run `uv run python tools/desk_coverage.py`."),
        "",
        f"**The preset layer** is {n} controls: the device knobs D1–D8, the track knobs "
        "K1–K8, the track faders S1–S8, and every other control the factory map gives a "
        "preset-layer row (" + ", ".join(c.glyph for c in controls if not is_strip(c))
        + "), less any control the session holds on both layers. Each preset is loaded as "
        f"the app loads it, from a scratch library holding {source}.",
        "",
        (f"**{MARK[MAPPED]} mapped**: a preset row is on the control and the preset can show "
         f"its param. **{MARK[DARK]} dark**: nothing is on it. **{MARK[DEAD]} dead**: a row is "
         "on it, but the preset cannot show the param — a pattern or bitmap knob with the "
         "faces off, points or lines opacity with that layer off, an effect's knob with the "
         "effects or that effect off, a look-back knob with the look-back off, a rotation "
         "rate or plane with rotation off (`learn.cannot_show`), or a param the registry "
         "lacks."),
        "",
        (f"The owner's bar for the authoring pass: **at most {BAR} dark or dead** on the "
         "preset layer. This run reports it; no preset is remapped to meet it."),
        "",
        "## Summary",
        "",
        "| preset | mapped | dark | dead | dark + dead | bar |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for r in rows:
        dd = r.count(DARK) + r.count(DEAD)
        out.append(f"| {r.name} | {r.count(MAPPED)} | {r.count(DARK)} | {r.count(DEAD)} | {dd} "
                   f"| {'met' if dd <= BAR else f'{dd - BAR} over'} |")
    met = sum(r.count(DARK) + r.count(DEAD) <= BAR for r in rows)
    out += ["", f"{met} of {len(rows)} presets meet the bar.", "",
            "## Preset × control", "",
            f"{MARK[MAPPED]} mapped · {MARK[DARK]} dark · {MARK[DEAD]} dead", "",
            "| preset | " + " | ".join(c.glyph for c in controls) + " |",
            "| --- | " + " | ".join(":-:" for _ in controls) + " |"]
    for r in rows:
        out.append(f"| {r.name} | " + " | ".join(MARK[c.status] for c in r.cells) + " |")
    out += ["", "## Dead controls", ""]
    dead = [(r.name, c) for r in rows for c in r.cells if c.status == DEAD]
    if dead:
        out += ["| preset | control | param | why |", "| --- | --- | --- | --- |"]
        out += [f"| {name} | {c.glyph} | `{c.target}` | {c.why} |" for name, c in dead]
    else:
        out.append("None.")
    out += ["", "## Rows off the preset layer's controls", "",
            "Preset rows on a control this table does not count (a free button).", ""]
    extra = [(r.name, e) for r in rows for e in r.extra]
    if extra:
        out += [f"- {name}: {e}" for name, e in extra]
    else:
        out.append("None.")
    return "\n".join(out) + "\n"


def build(library: Path | None = None) -> str:
    """The report over a scratch home made and removed here. The library
    home variable points at it too while it runs, so nothing can reach the
    owner's home."""
    before = os.environ.get("HYPERSPACE_HOME")
    with tempfile.TemporaryDirectory(prefix="desk-coverage-") as tmp:
        home = Path(tmp) / "home"
        home.mkdir()
        os.environ["HYPERSPACE_HOME"] = str(home)
        try:
            controls, rows = coverage(home, library)
        finally:
            if before is None:
                os.environ.pop("HYPERSPACE_HOME", None)
            else:
                os.environ["HYPERSPACE_HOME"] = before
    if library is None:
        return report(controls, rows)
    return report(controls, rows, "the factory presets and a library's presets and desk "
                                  "templates (copied in)")


def read_report() -> str | None:
    """The committed report's text (UTF-8, newlines as written), or None."""
    if not REPORT.exists():
        return None
    with open(REPORT, encoding="utf-8", newline="") as f:
        return f.read()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--check", action="store_true", help="exit 1 if the committed report is stale")
    ap.add_argument("--stdout", action="store_true", help="print the report; write nothing")
    ap.add_argument("--library", type=Path, default=None,
                    help="also report this library's presets (copied, never written)")
    args = ap.parse_args(argv)
    if args.check and (args.library is not None or args.stdout):
        ap.error("--check compares the factory report with the committed file: "
                 "it takes neither --library nor --stdout")
    text = build(args.library)
    if args.stdout or args.library is not None:
        sys.stdout.write(text)
        return 0
    if args.check:
        if read_report() != text:
            print(f"{REPORT.relative_to(ROOT)} is stale: run tools/desk_coverage.py",
                  file=sys.stderr)
            return 1
        return 0
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    # UTF-8 and "\n" whatever the platform: the text holds ● · ✕ — ×, and
    # the test compares bytes
    with open(REPORT, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"wrote {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
