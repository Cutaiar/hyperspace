# Review — 39-T1 (alpha is honest), PR #252

**Task quality: Approved.** The change is the one condition the spec asked
for (`render.draw_scene`: the cut-through blend on the window's
`Renderer.bg_alpha`, not a laid-over scene's zero ground), it leaves overlay
mode and every factory preset's picture unchanged (the reviewer read all 25:
none wires `backdrop.scene`; `party-tracer`/`party-wake` put the scene in
`composite.under`), the test fails on the base (alpha squared, 0.5 → 0.25)
and asserts both requirements, the re-record is exactly the eight frames
ruling 9 allowed plus the digest.

Cannot verify: the owner's Drive presets — any wiring a scene into
`backdrop.scene` or a composite's `over` now looks different on an opaque
window with cut-through on (the intended change; hand check AJ.10).

Minors (applied by the implementer before merge): the comment names the
backdrop case too; the register row's rough edge (overlay + laid-over scene
still squares alpha, by the spec); AJ.10 names the explicit
`scene → backdrop.scene` wire. Optional, not done: a test of overlay +
laid-over scene (unchanged by construction).
