"""Where the generators read and write.

Everything generated lands in the app's data directory, which Vite serves at
/data. One copy of each artefact: a second copy drifts the moment anything is
regenerated. work/ is scratch (intermediate target bitmaps, contact sheets)
and is gitignored.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "app" / "public" / "data"
WORK = ROOT / "work"

WEB = DATA          # the name the generators have always used
DATA.mkdir(parents=True, exist_ok=True)
WORK.mkdir(exist_ok=True)
