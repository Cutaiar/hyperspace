# Glossary

**Awaiting the owner's signature** (wave 4, D5a's PR). One row per concept, in the
owner's words, from `plans/wave-4-session-prompt.md`: "The semantic migration" and the
fourth round, 2026-11-04.

New code uses these words now. Old names stay until SEM renames them, once; no PR
renames in passing. **Code in SEM, files in the format lane:** a saved key or id is
a format move and rides the one migration. If it cannot change cheaply it stays, and the
last column says so.

There are two layers and no others. **The meta controller** is everything set for a
performance or an install. **The preset** is where anything can change anything, a
complete look you can play. Neither may leak into the other, and no preset can affect
another preset.

| Word | What it is | The code's old names it replaces | Does a saved name change? |
| --- | --- | --- | --- |
| **meta controller** | Everything set or tuned for a performance or an install, and not actively changed during one. Owns the two `Deck`s and says which `Deck` each controller, the keys, the mouse and the panel are on. In code: `deck.MetaController` | `session` (`SessionRegistry`, `SessionTable`, `part_of == "session"`), `rig` (`RigWires`, `RigMade`, `Presets.rig`), lowercase "deck" in prose | **Not yet decided.** `session` in a show file and `config.toml`'s words are saved names: format lane, or they stay and this row says so. `config.toml.rig` and the venues of #223 are its install side, asked at SEM |
| **preset** | A complete visual look you can play, where anything can change anything: its values, graph, routes and desk layer | "performance" (`part_of == "performance"`, `PERFORMANCE_GROUPS`), "look" in prose where it means the file. "Patch" stays: a piece of a preset, not a second layer | No: `presets/` and the `preset/…` schema already say it. `part_of`'s string is not saved |
| **`Deck`** | A loaded preset inside the meta controller: the objects one preset runs on (`deck.Deck`). There are exactly two. "Slot" is not a type: on air and off air say which `Deck` | `Deck` stays. "Deck 1", "deck 2" in comments stay until SEM's words pass; lowercase "deck" meaning the rig goes (row one). `Decks`, plan 44's name, was never built | None saved |
| **on air** | The `Deck` the outputs show. From D5c, whichever the crossfader is closer to. Until then deck 1. In code: `MetaController.on_air` | "program", "the deck on air", `Fade.on_air`, `session.lead` | None saved. `output.hold`, `.take`, `.drop` go in D5d |
| **off air** | The other `Deck`: built, explored and loaded into without the room seeing it. In code: `MetaController.off_air` | "preview", "held", `Host.off_air`, `Fade.off_air`, `MediaIO.off_air` | None saved |
| **player** | A named actor, player 1 to 4, who registers any number of controllers and holds a duty. A preset names a player, never a device. In code from PL: `Player` | Plan 27's roles (`axis@p2`) are the seam. Bare `pad:` and `axis:` rows read as player 1 | None today: bare rows stay as they are, with no file change. Node mode's saved player names arrive in NM0, format lane |
| **duty** | What a player is on: on air or off air. It stays until someone moves the player. In code from PL: `Duty` | Nothing yet | None |
| **controller** | One physical input a player holds: the APC40, a pad, a Joy-Con, the hands. Generic: what it does comes from rows, not from what it is. In code, one device (`devices.Base`) with its own `Pointer`, keyed by role | "device" for an input, "desk" for the APC40 (`desk.*` ids stay), "pad" where it means any of them | `[[devices]]` and `role` in `config.toml`, and `desk.*` ids: no, they stay. NSEW renames only the buttons, in the format lane |
| **analyzer** | What listens to the room and makes the lanes every preset may wire from: a fixture on the graph. Its tuning is the meta controller's; what plugs into it is the preset's. In code `analyzer.py` already says it | `band` in words (336 uses), the "bands" pages. A band is still one of its frequency ranges | **Words first (AZ).** `band.*` ids and the `band` group: format lane, or never. If they stay, they stay here as ids |
| **node mode** | A controller pointed at one node of a preset, its degrees of freedom filled by that node's params. The controller's choice, entered from the panel; a cable of its own kind and colour, saved in the preset | Nothing yet. Plan 53's "temporary cables" and "keep this one" are gone | New in NM0: player, node and cable kind are saved, format lane |
| **crossfade** | Moving the outputs between the two `Deck`s, as a DJ mixer's crossfader: the APC's crossfader. Fading into an empty `Deck` is black. One of two verbs left, with "copy on air to off air"; a timed fade is a control on it. In code `Fade`, `Mix`, `output.xfade` | TAKE, DROP, HOLD (`hold.py`, gone in D5d), "swap" (there is none), "the mix", "the take" | `output.xfade` and `output.xfade_s` keep their ids: never saved in a preset. A learned row on one stays |
| **dim** | The master level of the whole picture, the meta controller's: the APC's MASTER fader from D5d. Separate from the crossfade | "the crossfader" as it reads on the desk today (the desk's crossfader row goes to `output.xfade` in D5d) | `output.dim` keeps its id |
