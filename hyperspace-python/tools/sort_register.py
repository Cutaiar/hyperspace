"""Sort docs/DECISION-REGISTER.md by row number, changing no text: the answer
sheet's rows, and the `### <n>.` sections from the first numbered <first> or
more (544 by default; the older ones keep their plan grouping) to the last,
a `## ` heading (and any unnumbered `### ` under it) moving with the section
under it, an unnumbered `### ` elsewhere staying in the section before it, and
a tail after the last section (a `## ` with no numbered section under it)
left in place (row 606). `uv run python tools/sort_register.py [first] [path]`."""
import re
import sys
from itertools import pairwise
from pathlib import Path

first = int(sys.argv[1]) if len(sys.argv) > 1 else 544
path = Path(sys.argv[2] if len(sys.argv) > 2 else Path(__file__).parents[1] / "docs/DECISION-REGISTER.md")
lines, num = path.read_text().split("\n"), lambda s: int(re.match(r"\D*(\d+)", s).group(1))
numbered = lambda s: re.match(r"### \d", s) is not None
a = next(i for i, s in enumerate(lines) if re.match(r"\| \d", s))
b = next(i for i in range(a, len(lines)) if not re.match(r"\| \d", lines[i]))
lines[a:b] = sorted(lines[a:b], key=num)
heads = [i for i, s in enumerate(lines) if numbered(s)]
heads = heads[next(k for k, i in enumerate(heads) if num(lines[i]) >= first):]
back = [next((j for j in range(h - 1, -1, -1) if lines[j].startswith("## ") or numbered(lines[j])), h)
        for h in heads]
end = next((j for j in range(heads[-1] + 1, len(lines)) if lines[j].startswith("## ")), len(lines))
cuts = [c if lines[c].startswith("## ") else h for c, h in zip(back, heads)] + [end]
chunks = sorted((lines[c:d] for c, d in pairwise(cuts)), key=lambda ch: num(next(filter(numbered, ch))))
path.write_text("\n".join(lines[:cuts[0]] + [s for ch in chunks for s in ch] + lines[end:]))
