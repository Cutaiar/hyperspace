// @label Trip warp
// @order 20
// @blend mix
// @speed 0.25
// @tip Noita's trip distortion (post_final.frag, drugged_distortion_amount): the frame
// @tip zooms in up to 10 % and slides along two octaves of drifting noise, harder toward
// @tip the edges, so the centre stays readable while the rim swims.
// @clock u_drift_t drift*scale

uniform float u_amount;  // @param 0 2 0.2 amount "Amount" Noita's distortion amount — 0.2 on the first trip stage, 0.5 heavily tripping, ~1 with the stages stacked.
uniform float u_scale;   // @param 0.5 16 3 log "Scale" Noise cells across the frame's height: low is a slow heave, high a fine ripple. The field still slides the same screens a second; a step re-zooms it about the centre.
uniform float u_drift;   // @param 0 8 1 "Drift" How fast the noise field slides under the frame (Noita's rate at 1); a step changes the speed, never where the field is.

vec4 effect(vec2 uv) {
    vec2 p = centred(uv);
    // Noita: two samples of a noise texture, at 0.1 and 0.3 per screen,
    // scrolling 0.01 and 0.005 per second — here a screen and a third of a
    // screen per 10 s and 60 s. The scroll is counted in cells: u_drift_t
    // runs at speed × drift × scale (fx.py integrates it, @clock), so at
    // still knobs it is the old u_phase × drift × scale exactly, and a step
    // of drift or scale changes how fast the field slides, never where it
    // is — scale only re-zooms the cells about the centre
    vec2 pn = perlin2(p * u_scale + vec2(u_drift_t) * 0.1)
            + perlin2(p * u_scale * 3.0 + vec2(u_drift_t) * (0.0167 * 3.0) + 7.0);
    float zoom = min(1.0, u_amount * 1.5);
    vec2 w = (uv - 0.5) * mix(1.0, 0.9, zoom) + 0.5;
    vec2 q = w + pn * 0.2;
    return src(mix(w, q, length(uv - 0.5) * u_amount));
}
