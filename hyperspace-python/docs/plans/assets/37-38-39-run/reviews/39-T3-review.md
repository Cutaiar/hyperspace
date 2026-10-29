# Review — 39-T3 (cut), PR #260

**Task quality: Needs fixes** (one Important), then merge.

Sound: `CutNode` (image + mask → image, own size its picture's; no mask or
a mask making nothing → the picture through with no pass and no target);
one `CUT_FS` pass premultiplied, the mask fitted by cover (`u_scale`) and
flipped by `u_flip` through `graph.mask_of(node, frame) -> (tex, flipped)`;
made once a frame into its own `#cut` target (no pool aliasing), timed
alone; own-sized pictures handled as an effect does; `declare_cuts`
(invert off, amount 1); `view.CutState` and the `ui_presets` word on the
matte precedent; the cut-out fixture wired as W6 says (still → matte →
cut.mask; scene → kaleido → cut.image; cut → composite.over; scene →
composite.under) with 8 added goldens (the PNG: the patterned polytope
with a disc of kaleidoscope wedges right of centre); 23 real-pixel tests.

**Important** (ruled with the reviewer): `_Build.laid_over` stops at a
cut, so inserting one turns the kept area's see-through ground opaque —
against "where the mask passes, nothing changes" and the owner's
`fg → cut → composite.over` case. Fix: recurse through `cut.image` as
through `effect.image`; tests; the cut-out goldens re-recorded (a fixture
of this same task). Notes: `laid_over` also does not see through
`copy`/`resize`/`delay` (docs); the flip flag in `PROMOTE_FS`/`fit` is
T4's (added to its dispatch).
