"""Where the generators read and write.

DATA is the app's own data directory, served at /data, and is where generated
artefacts live now. LEGACY is web/, which still holds the two pages not yet
ported to the app -- the live solver and the sprite -- together with the blobs
only they read. It exists so those two keep working from a plain static server
during the port, and it goes away with them.

Keeping one copy of each artefact is the point: a second copy drifts the moment
anything is regenerated.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "app" / "public" / "data"
LEGACY = ROOT / "web"
WORK = ROOT / "work"

WEB = DATA          # default target for generators that feed the app
DATA.mkdir(parents=True, exist_ok=True)
WORK.mkdir(exist_ok=True)
