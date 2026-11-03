"""Where the generators read and write.

web/  is committed and served; work/ is scratch (intermediate target bitmaps,
contact sheets) and is gitignored.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
WORK = ROOT / "work"
WORK.mkdir(exist_ok=True)
