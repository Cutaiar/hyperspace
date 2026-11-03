"""Sort docs/DECISION-REGISTER.md by row number, changing no text: the answer
sheet's rows, and the `### <n>.` sections from the first numbered <first> or
more (544 by default; the older ones keep their plan grouping) to the end, a
`## ` heading moving with the section under it (row 606).
`uv run python tools/sort_register.py [first] [path]`."""
import re
import sys
from itertools import pairwise
from pathlib import Path

first = int(sys.argv[1]) if len(sys.argv) > 1 else 544
path = Path(sys.argv[2] if len(sys.argv) > 2 else Path(__file__).parents[1] / "docs/DECISION-REGISTER.md")
lines, num = path.read_text().split("\n"), lambda s: int(re.match(r"\D*(\d+)", s).group(1))
a = next(i for i, s in enumerate(lines) if re.match(r"\| \d", s))
b = next(i for i in range(a, len(lines)) if not re.match(r"\| \d", lines[i]))
lines[a:b] = sorted(lines[a:b], key=num)
heads = [i for i, s in enumerate(lines) if re.match(r"### \d", s)]
heads = heads[next(k for k, i in enumerate(heads) if num(lines[i]) >= first):]
cuts = [next((j for j in range(h - 1, -1, -1) if lines[j].startswith(("## ", "### "))), h)
        for h in heads]
cuts = [c if lines[c].startswith("## ") else h for c, h in zip(cuts, heads)] + [len(lines)]
chunks = sorted((lines[c:d] for c, d in pairwise(cuts)), key=lambda ch: num(next(
    s for s in ch if s.startswith("### "))))
path.write_text("\n".join(lines[:cuts[0]] + [s for ch in chunks for s in ch]))
