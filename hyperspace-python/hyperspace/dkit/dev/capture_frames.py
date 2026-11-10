"""Hash every frame of a set of dashboard scenarios, and the ImGui gallery.

The check for a change that must not move a pixel (RETRO rows 84-85):

    xvfb-run -a uv run python -m hyperspace.dkit.dev.capture_frames before.json ld
    ... change ...
    xvfb-run -a uv run python -m hyperspace.dkit.dev.capture_frames after.json ld
    uv run python -m hyperspace.dkit.dev.capture_frames --compare before.json after.json

and again with "dl". Every frame of every scenario is hashed - static, a
resize, a hover, a scroll that opens a row's menu and walks its items, the
tabs, the contact sheet and back, in each theme - via a shim over
glReadPixels, so a frame that differs in one byte is named. The order is
"ld" (light first) or "dl" (dark first): every scenario runs in ONE process,
so module-level caches carry across theme switches and resizes, which is
what a cache bug needs. Compare captures taken in the SAME order: 14
contact-sheet pixels depend on whether any render() ran before it in the
process (the font atlas's packing order; RETRO row 84). The first two
scenarios' last frames are saved as PNGs beside OUT.json.
"""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from hyperspace.dkit.dev import dashboard as DB

hashes = []


class GLShim:
    def __init__(self, gl):
        self._gl = gl

    def __getattr__(self, k):
        return getattr(self._gl, k)

    def glReadPixels(self, *a, **k):
        raw = self._gl.glReadPixels(*a, **k)
        hashes.append(hashlib.sha1(bytes(raw)).hexdigest()[:16])
        return raw


DB.GL = GLShim(DB.GL)
W, H = 1440, 1100
PNG_DIR = None


def run(name, theme, w, h, script=None, keys=None):
    hashes.clear()
    f = DB.render(theme, w, h, script=script, keys=keys, keep="last")
    if PNG_DIR and name in ("static", "small"):
        from PIL import Image
        Image.fromarray(f[-1]).save(Path(PNG_DIR) / f"dash-{theme}-{name}.png")
    return name, list(hashes)


def scenarios(theme):
    out = []
    out.append(run("static", theme, W, H))
    out.append(run("small", theme, 1100, 800))
    out.append(run("static-again", theme, W, H))
    r = DB.lay_out(W, H)
    nx, ny, nw, nh = r.nav[2]
    spot = (nx + nw / 2, ny + nh / 2)
    away = (W - 40, H - 40)
    out.append(run("hover", theme, W, H, [away] * 2 + [spot] * 14 + [away] * 14))
    # scroll to bottom, hover a row, open its kebab menu, hover items
    px, py = W / 2 + 120, H / 2
    pre = [(px, py)] * 4 + [(px, py, False, -3.0)] * 60 + [(px, py)] * 4
    hashes.clear()
    DB.render(theme, W, H, script=pre, keep="last")
    sy = DB.render.last_state["page_scroll"]
    rr = DB.lay_out(W, H, body_dy=-sy)
    rx, ry, rw, rh = rr.table_rows[1]
    kx, ky = rx + rw - 30 + 13, ry + rh / 2
    script = (pre + [(rx + 100, ry + rh / 2)] * 6 + [(kx, ky)] * 12
              + [(kx, ky, True)] * 2 + [(kx, ky, False)] * 10)
    out.append(run("menu", theme, W, H, script))
    import menu as M
    mr = M.LAST_RECT.get("rowmenu.1")
    if mr:
        mx, my, mw, _mh = mr
        for i in range(3):
            script += [(mx + mw / 2, my + M.PAD + M.ITEM_H * i + M.ITEM_H / 2)] * 6
        out.append(run("menu-items", theme, W, H, script))
    # tabs: click tab 2 then tab 4
    ty = r.table_tabs[1] + 16
    s2 = []
    for x in (445, 567):
        s2 += [(x, ty)] * 6 + [(x, ty, True)] * 2 + [(x, ty, False)] * 6
    out.append(run("tabs", theme, W, H, s2))
    # gallery nav (contact sheet), then back
    gx, gy, gw, gh = r.nav[1]
    g = (gx + gw / 2, gy + gh / 2)
    o = (r.nav[0][0] + 50, r.nav[0][1] + 16)
    s3 = ([g] * 4 + [(*g, True)] * 2 + [(*g, False)] * 8
          + [(700, 600)] * 4 + [(700, 600, False, -2.0)] * 10
          + [o] * 4 + [(*o, True)] * 2 + [(*o, False)] * 6)
    out.append(run("nav-gallery", theme, W, H, s3))
    out.append(run("small-again", theme, 1100, 800))
    return out


def gallery(theme):
    with tempfile.TemporaryDirectory() as d:
        subprocess.run([sys.executable, "-m", "hyperspace.dkit.dev.gallery", "--out", d,
                        "--theme", theme], check=True, capture_output=True)
        return hashlib.sha1((Path(d) / "imgui.png").read_bytes()).hexdigest()[:16]


def compare(pa, pb) -> int:
    a, b = (json.loads(Path(p).read_text()) for p in (pa, pb))
    bad = 0
    for k in sorted(set(a) | set(b)):
        va, vb = a.get(k), b.get(k)
        if va == vb:
            continue
        bad += 1
        if isinstance(va, list) and isinstance(vb, list):
            d = [i for i, (x, y) in enumerate(zip(va, vb)) if x != y]
            print(f"DIFF {k}: {len(d)} of {len(va)}/{len(vb)} frames, "
                  f"first {d[:5]}")
        else:
            print(f"DIFF {k}")
    n = sum(len(v) if isinstance(v, list) else 1 for v in a.values())
    print("IDENTICAL" if not bad else f"{bad} scenarios differ",
          f"({n} frames, {len(a)} scenarios)")
    return 1 if bad else 0


def main():
    if sys.argv[1] == "--compare":
        raise SystemExit(compare(sys.argv[2], sys.argv[3]))
    dest = sys.argv[1]
    order = sys.argv[2] if len(sys.argv) > 2 else "ld"
    global PNG_DIR
    PNG_DIR = str(Path(dest).with_suffix(""))
    Path(PNG_DIR).mkdir(exist_ok=True)
    themes = ["light", "dark"] if order == "ld" else ["dark", "light"]
    res = {}
    for t in themes:
        for name, hs in scenarios(t):
            res[f"{t}/{name}"] = hs
    for t in themes:
        res[f"gallery/{t}"] = gallery(t)
    Path(dest).write_text(json.dumps(res, indent=1, sort_keys=True))
    n = sum(len(v) if isinstance(v, list) else 1 for v in res.values())
    print(f"{dest}: {n} frames")


if __name__ == "__main__":
    main()
