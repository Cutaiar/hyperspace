// @label Cell action
// @order 16
// @family field
// @makes field
// @takes image field
// @takes field field
// @tip What a cell does with a number: shift sideways, zoom, stretch along one way until
// @tip it streaks, turn, bulge like a lens, or trade places with the block beside it.
// @tip The number comes into its input (a Waveform over a Measure of cells, which brings
// @tip the cell's size with it); the pixel's place in its cell into its field port (a
// @tip second Measure of cells, Out direction). Its output is the push in half frame
// @tip heights: wire it into Displace's field port at Amount 0.5 (its top) to push by it
// @tip exactly. Blocks, taken apart.

// The third of DISTORTION.md's questions for a grid of cells — the
// actions of blocks.glsl, read from fields instead of worked out inside, so
// `measure (cells) → waveform → cell action ← measure.2 → displace` is Blocks
uniform float u_amount; // @param 0 4 0.5 amount "Amount" How much a cell does at its number's peak — shift: cells moved; zoom, stretch and bulge: doublings of size; turn: quarter turns; swap: trades at the peak, none at the trough.
uniform int u_action;   // @param choice [shift|zoom|stretch|turn|bulge|swap] 0 "Action" What a cell does with its number.
uniform float u_angle;  // @param 0 6.2832 0 wrap "Angle" Shift and stretch: the way they go, radians (0 across). Swap: blocks trade across or up and down, whichever the angle is nearer (the Measures' Pairs says which blocks pair).

vec4 effect(vec2 uv) {
    vec4 w = field_in(uv), k = field_port(uv);
    float a = w.x * u_amount;
    vec2 cs = w.yz;                                     // a cell, frame heights (rides with the number)
    vec2 at = k.xy * cs;                                // this pixel's place in its cell, frame heights
    vec2 dir = vec2(cos(u_angle), sin(u_angle));
    vec2 d;
    if (u_action == 1) {
        d = at * (exp2(a) - 1.0);
    } else if (u_action == 2) {
        d = dir * dot(at, dir) * (exp2(a) - 1.0);
    } else if (u_action == 3) {
        d = rot(a * 0.5 * PI) * at - at;
    } else if (u_action == 4) {
        // a lens inside the cell's inscribed circle, still at its rim
        float rr = length(at) * 2.0 / min(cs.x, cs.y);
        d = rr < 1.0 ? at * (pow(max(rr, 1e-4), exp2(a) - 1.0) - 1.0) : vec2(0.0);
    } else if (u_action == 5) {
        // the pair's number counts trades (none at its trough, Amount at its
        // peak); an odd count is a trade. k.z is this block's side × Group
        vec2 ax = abs(dir.x) >= abs(dir.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
        float n = floor(0.5 * (a + u_amount) + 0.5);
        d = mod(n, 2.0) > 0.5 ? ax * k.z * cs : vec2(0.0);
    } else {
        d = dir * a * cs;
    }
    // in half frame heights, so Displace at its top Amount (0.5) pushes by d
    // exactly (×2 then ×½ is exact): a field's push that reached 1 would ask
    // Displace's Amount to reach 1, a format change for every saved route on it
    return as_vector(d * 2.0);
}
