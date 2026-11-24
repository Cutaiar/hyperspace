// @label Noise
// @order 32
// @family field
// @makes field
// @takes image none
// @takes field field
// @tip A field of smooth noise, about −1 … 1, Scale blobs to a frame height, laid from
// @tip the point (a Point on its field port; the middle with none) — move the Point and
// @tip the noise slides with it.

// plan 67 §15: Measure's noise, on its own
uniform float u_scale;  // @param 0.0625 64 1 log "Scale" Blobs to a frame height.

vec4 effect(vec2 uv) { return as_scalar(perlin(from_field_point(uv) * u_scale) * 2.0); }
