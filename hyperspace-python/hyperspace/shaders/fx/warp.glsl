// @label Trip warp
// @order 20
// @blend mix
// @tip Noita's trip distortion (post_final.frag, drugged_distortion_amount): the frame
// @tip zooms in up to 10 % and slides along two octaves of drifting noise, harder toward
// @tip the edges, so the centre stays readable while the rim swims.

uniform float u_amount;  // @param 0 2 0.5 "Amount" Noita's distortion amount — 0.2 on the first trip stage, 0.5 heavily tripping, ~1 with the stages stacked.
uniform float u_scale;   // @param 0.5 16 3 log "Scale" Noise cells across the frame's height: low is a slow heave, high a fine ripple.
uniform float u_drift;   // @param 0 8 1 "Drift" How fast the noise field slides under the frame (Noita's rate at 1).

vec4 effect(vec2 uv) {
    vec2 p = centred(uv);
    float t = u_phase * u_drift;
    // Noita: two samples of a noise texture, at 0.1 and 0.3 per screen,
    // scrolling 0.01 and 0.005 per second — here a screen and a third of a
    // screen per 10 s and 60 s, in cells of u_scale
    vec2 pn = perlin2((p + vec2(t) * 0.1) * u_scale)
            + perlin2((p + vec2(t) * 0.0167) * u_scale * 3.0 + 7.0);
    float zoom = min(1.0, u_amount * 1.5);
    vec2 w = (uv - 0.5) * mix(1.0, 0.9, zoom) + 0.5;
    vec2 q = w + pn * 0.2;
    return src(mix(w, q, length(uv - 0.5) * u_amount));
}
