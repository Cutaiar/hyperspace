// @label Wobble
// @order 25
// @blend mix
// @tip Minecraft's "wobble" (Super Secret Settings, wobble.fsh): every row slides sideways
// @tip on a sine of its height and every column bobs on a cosine of its x, both running
// @tip once a second — the classic trig wobble, wavy like heat over a road.

uniform float u_amount;  // @param 0 0.05 0.006 "Amount" Displacement in frame units (Minecraft: 0.002).
uniform float u_freq;    // @param 1 600 30 log "Frequency" Ripples, radians per frame height (Minecraft: 288 — a fine shiver).
uniform float u_swirl;   // @param 0 1 0 "Swirl" Feeds each axis's wave into the other, so straight ripples curl.

vec4 effect(vec2 uv) {
    float t = u_phase * TAU;
    vec2 p = uv * vec2(u_res.x / u_res.y, 1.0);   // square radians on any aspect
    float sy = sin(p.y * u_freq + t);
    float cx = cos(p.x * u_freq + t);
    vec2 off = vec2(sin(p.y * u_freq + t + u_swirl * 3.0 * cx),
                    cos(p.x * u_freq + t + u_swirl * 3.0 * sy)) * u_amount;
    return src(uv + off);
}
