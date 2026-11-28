// @label Read
// @order 6
// @family past
// @takes image none
// @takes stack stack
// @tip A frame from the past: wire a delay into its stack, and it shows the frame At
// @tip frames back (0 the newest the delay keeps; the delay's Depth is how many it keeps
// @tip and its rate how far apart). A fraction blends the two either side, unless Between
// @tip says nearest. At takes a field like any knob: a field across the frame shows each
// @tip pixel a different moment — a slit-scan, a time displace.

// an echo is a read of the stack at one index, and time displace is the
// same read with a field on At
uniform float u_at;      // @param 0 63 0 "At" How many frames back, 0 the newest the delay keeps. Past what it keeps, its oldest.
uniform int u_between;   // @param choice [blend|nearest] 0 "Between" A fraction of a frame: the two either side blended, or the nearer alone (hard steps).

vec4 effect(vec2 uv) { return stack_at(u_at, uv, u_between == 1); }
