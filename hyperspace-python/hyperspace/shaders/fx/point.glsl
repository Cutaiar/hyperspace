// @label Point
// @order 11
// @family field
// @makes field
// @takes image none
// @tip A place on the frame, as a field: at every pixel, the way and distance from the
// @tip point to it (frame heights), a vector. Wire it into a Line, Rings, Spokes, Cells or
// @tip Noise to say where they count from — one Point can move every one of them at once.
// @tip X and Y are ordinary knobs: an LFO, a hand or a band can drive them.

// plan 67 §15: `point` is one primitive (§3.3), a field of offsets from it;
// the measures read it on their field port instead of a Centre X / Y each
uniform float u_x;  // @param -1 1 0 "X" Where across: −1 the left edge, 0 the middle, +1 the right edge.
uniform float u_y;  // @param -1 1 0 "Y" Where up and down: −1 the bottom edge, 0 the middle, +1 the top.

vec4 effect(vec2 uv) { return as_vector(from_point(uv, u_x, u_y)); }
