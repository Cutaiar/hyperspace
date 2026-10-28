# Review — 39-T4 (segment: the node and the worker), PR #265

**Task quality: Needs fixes** (two Important), then merge.

Sound: `segment.py` on `DreamWorker`'s shape (three slots, a race-free
`taken` set, submit never waits, latest wins, drops counted, errors to
`.error` cleared by the next good result, sleeps on the condition,
`close` joins 1 s); Vision lifted from the bench script (request cached
per level, `kCGImageAlphaNoneSkipLast`, L008 locked/read past padding/
unlocked, imports in `open()`); torch (the spike's normalise/softmax,
class 15, fp16 on MPS, `weights_backbone=None`, one model per
(device, dtype) behind a lock); `pick_backend` via `find_spec`, a missing
library a reason string and no thread. Boundaries: graph reaches the
worker through `frame.r.segmenter`; the banned set gains `segment` and
`Vision`; `test_app_boundary` gains `hyperspace.segment`, `Vision`,
`CoreML`, `torchvision`; `masks.py` a leaf. The node: pins in `PINS` and
`_SEGMENT_PIN` for `segment.N`; every "nothing yet" case said; `on` off
never feeds the worker; the moved key (channel, frame id, quality); the
shortcut also requires a cover fit and no `alpha_of` (justified). The
flip honoured everywhere (`PROMOTE_FS`, `fit`, `MaskPicture`, a shared
`mask_port`), tested on a cut, a window and `lookback.cover`. Motion: a
strict pair, k = 1 − exp(−dt/learn). The plan 38 seam: `segment_cfg`
None → no worker; `close` closes only its own; tested on a mirrored
renderer. Params: person/fast/0/0/on/0.1/3; mode and quality not
modulatable. Goldens +8 `segment-motion` (the polytope with the still's
disc cut away); live tests under `--all` only, synthetic frames. Vision's
matte verified 4:3 or 3:4 following the input's orientation, so the
resample to the frame's aspect is the right reading.

**Important 1**: `smooth` re-quantises to uint8 each result — a permanent
ghost near 1 (AJ.3's fail mode). **Important 2**: `laid_over` does not see
through a segment (the rule T3 was held to). Minors: a row for fg/bg at
the frame's size; the doubled backend name; the frame-thread join; the
exit deadline shared; the live-test marker convention; a several-workers
test; for T5 `segment.2`'s pins not drawn; for integration
`hold.PROGRAM_IDS` entries.
