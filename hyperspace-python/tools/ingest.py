#!/usr/bin/env python3
"""Download a YouTube video or Instagram reel into the media folder as MP4.

    uv run python tools/ingest.py URL [--name NAME] [--shared] [--max-height N]

A thin wrapper over the installed ``yt-dlp`` (it must be on PATH, with
``ffmpeg`` beside it for the merge). The file lands where the MEDIA page
already looks:

- default: this Mac's own folder, ``<home>/media/`` (``$HYPERSPACE_HOME``,
  else ~/Hyperspace);
- ``--shared``: the cloud folder, ``<library>/media/`` — the config's
  ``[library] path`` — so the other Mac sees it too.

The file is named after ``--name``, else the video's title, slugged the way
preset files are (``Ketchup & Marceline!`` → ``ketchup-marceline.mp4``);
a name already taken gets ``-2``, ``-3``, … rather than overwriting.

H.264 video and AAC audio are preferred (PyAV decodes anything, but H.264
is cheapest to scrub), at most ``--max-height`` lines tall (default 1080,
the render cap); yt-dlp merges or remuxes into an MP4. A login-walled reel
can be fetched with ``--cookies-from-browser chrome`` (passed through).

Exit status: yt-dlp's own, 2 when yt-dlp is not installed.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MEDIA = "media"


def media_dir(shared: bool) -> Path:
    """`<library>/media/` when `shared`, else `<home>/media/` (app._open_media's
    two folders). Exits when --shared is asked for with no library set."""
    from hyperspace import config, library
    home = Path(library.home())
    if not shared:
        return home / MEDIA
    cfg_path = home / config.FILE
    lp = config.load(cfg_path).get("library", {}).get("path", "") if cfg_path.is_file() else ""
    if not lp:
        sys.exit(f"no shared folder: set [library] path in {cfg_path}")
    return Path(lp) / MEDIA


def title_of(ytdlp: str, url: str, extra: list[str]) -> str:
    """The video's title, asked of yt-dlp without downloading."""
    out = subprocess.run([ytdlp, "--no-playlist", "--skip-download", "--print", "title", *extra, url],
                         capture_output=True, text=True, check=False)
    if out.returncode != 0:
        sys.stderr.write(out.stderr)
        sys.exit(out.returncode)
    return out.stdout.strip().splitlines()[0] if out.stdout.strip() else "untitled"


def free_path(folder: Path, stem: str) -> Path:
    """`<folder>/<stem>.mp4`, or the first `<stem>-<n>.mp4` not taken."""
    path, n = folder / f"{stem}.mp4", 2
    while path.exists():
        path, n = folder / f"{stem}-{n}.mp4", n + 1
    return path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("url", help="a YouTube or Instagram reel URL")
    ap.add_argument("--name", help="the file's name (default: the video's title), slugged")
    ap.add_argument("--shared", action="store_true", help="save into <library>/media/ instead of <home>/media/")
    ap.add_argument("--max-height", type=int, default=1080, help="tallest video to fetch (default 1080)")
    ap.add_argument("--cookies-from-browser", metavar="BROWSER", help="passed to yt-dlp, for login-walled reels")
    args = ap.parse_args(argv)

    ytdlp = shutil.which("yt-dlp")
    if not ytdlp:
        print("yt-dlp is not installed: brew install yt-dlp", file=sys.stderr)
        return 2
    extra = ["--cookies-from-browser", args.cookies_from_browser] if args.cookies_from_browser else []

    from hyperspace.library import slug
    folder = media_dir(args.shared)
    folder.mkdir(parents=True, exist_ok=True)
    out = free_path(folder, slug(args.name or title_of(ytdlp, args.url, extra)))

    h = args.max_height
    cmd = [ytdlp, "--no-playlist",
           "-f", f"bv*[height<={h}]+ba/b[height<={h}]/bv*+ba/b",
           "-S", "vcodec:h264,acodec:aac",
           "--merge-output-format", "mp4", "--remux-video", "mp4",
           "-o", f"{out.with_suffix('')}.%(ext)s", *extra, args.url]
    rc = subprocess.run(cmd, check=False).returncode
    if rc == 0:
        print(f"saved {out}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
