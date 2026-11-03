# The panel's fonts

Bundled so the control panel draws, and its tests measure, the same on
every machine (`ui.py`, "font atlas"; docs/ENGINEERING.md §16). Each file
is the family's own release, unmodified: Google Fonts' served copies
strip the symbol ranges the panel draws.

| File | Role | Source | Licence |
| --- | --- | --- | --- |
| `Inter-Medium.ttf` | words (`ui`) | [Inter 4.1](https://github.com/rsms/inter/releases/tag/v4.1), `extras/ttf/` | SIL OFL 1.1, `Inter-LICENSE.txt` |
| `Inter-Bold.ttf` | tracked labels (`micro`) | the same | the same |
| `JetBrainsMono-SemiBold.ttf` | numbers (`num`) | [JetBrains Mono 2.304](https://github.com/JetBrains/JetBrainsMono/releases/tag/v2.304), `fonts/ttf/` | SIL OFL 1.1, `JetBrainsMono-OFL.txt` |
| `DejaVuSans.ttf` | symbols, merged behind every face | [DejaVu 2.37](https://github.com/dejavu-fonts/dejavu-fonts/releases/tag/version_2_37), `ttf/` | Bitstream Vera / public domain, `DejaVu-LICENSE.txt` |

DejaVu Sans covers every non-ASCII character the panel's strings use
(arrows, ⇧ ⌘, ● ○ ▸ ▾, Greek, ≈ ≥ √, superscripts, planet symbols);
Inter and JetBrains Mono draw what they have and DejaVu the rest.
