// @label Trip colour
// @order 80
// @blend mix
// @tip Noita's trip colour (drugged_color_amount): the green channel pumps with the
// @tip frame's brightness on a slow sine, so white swings between magenta and hot green
// @tip and everything else shifts with it. A grain of noise keeps it alive.

uniform float u_amount;  // @param 0 2 0.4 "Amount" Noita's colour amount — 0.05 on the first stage, 0.4 heavily tripping, 1.5 on the last; above 1 it overshoots.
uniform float u_pulse;   // @param 0.1 6 1.5 log "Pulse" The sine's rate, rad/s (Noita: 1.5).

vec4 effect(vec2 uv) {
    vec4 c = src(uv);
    float b = peak(c.rgb);
    float grain = hash21(floor(uv * u_res) + floor(u_time * 60.0));
    // quoted: c.g = mix(c.g, b*2*c.g*(sin(time*1.5)+1)*0.5 + noise.b/64, amount)
    c.g = mix(c.g, b * 2.0 * c.g * (sin(u_phase * u_pulse) + 1.0) * 0.5 + grain / 64.0,
              u_amount);
    return max(c, 0.0);
}
