// @label Noise
// @order 32
// @family field
// @speed 1
// @clock u_drift_t drift*scale
// @makes field
// @takes image none
// @takes field field
// @tip A field of smooth noise, Scale blobs to a frame height, laid from the point (a
// @tip Point on its field port; the middle with none) — move the Point and the noise
// @tip slides with it. Out value is one octave, about −1 … 1; Out flow is two octaves as
// @tip a vector, Trip warp's: wire it into Displace and the frame swims. Drift slides
// @tip the noise under the frame.

// plan 67 §15: Measure's noise, on its own; flow is warp.glsl's two drifting
// octaves (Noita's), so Trip warp is a patch (plan 67, Trip warp as a patch)
uniform float u_scale;  // @param 0.0625 64 1 log "Scale" Blobs to a frame height.
uniform int u_out;      // @param choice [value|flow] 0 "Out" Value: one octave, a scalar field. Flow: two octaves as a vector, x and y each about −1 … 1, the way Trip warp's frame swims.
uniform float u_drift;  // @param 0 8 0 "Drift" How fast the noise slides under the frame; 0 holds it still. A step changes the speed, never where the noise is.

vec4 effect(vec2 uv) {
    vec2 p = from_field_point(uv);
    if (u_out == 1)
        return as_vector(perlin2(p * u_scale + vec2(u_drift_t) * 0.1)
                         + perlin2(p * u_scale * 3.0 + vec2(u_drift_t) * (0.0167 * 3.0) + 7.0));
    return as_scalar(perlin(p * u_scale + vec2(u_drift_t) * 0.1) * 2.0);
}
