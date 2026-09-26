// @label Glimmer
// @order 70
// @blend add
// @tip Sparkle: four-point glints that flare and fade on and around whatever is lit,
// @tip each on its own clock and in its own iridescent colour.

uniform float u_amount;  // @param 0 3 1 "Amount" Brightness of the glints.
uniform float u_density; // @param 0 1 0.25 "Density" How many cells can hold a glint.
uniform float u_size;    // @param 3 64 16 log "Size" Glint cell size, px — the star spans about one cell.
uniform float u_halo;    // @param 0 32 6 "Reach" How far from the lit pixels glints may appear, px.
uniform float u_ground;  // @param 0 1 0 "Ground" Glints over black too — a starfield.

vec4 effect(vec2 uv) {
    vec2 px = uv * u_res;
    vec3 glow = vec3(0.0);
    // the cell and its neighbours, so a star's arms cross cell borders
    vec2 base = floor(px / u_size);
    for (int j = -1; j <= 1; j++)
    for (int i = -1; i <= 1; i++) {
        vec2 cell = base + vec2(i, j);
        vec2 h = hash22(cell);
        if (h.x > u_density) continue;
        vec2 centre = (cell + 0.25 + 0.5 * hash22(cell + 7.1)) * u_size;
        float lit = max(reach(centre / u_res, u_halo), u_ground);
        if (lit <= 0.0) continue;
        // a short flare once per cycle, each cell on its own rate and phase
        float tw = 0.5 + 0.5 * sin(u_phase * (1.5 + 4.0 * h.y) + h.x * 97.0);
        tw = pow(tw, 6.0);
        // arms a pixel or so thick whatever the cell size, a cell long
        vec2 dp = abs(px - centre);
        vec2 d = dp / u_size;
        float core = exp(-dot(d, d) * 10.0);
        float arms = exp(-dp.x * 0.8) * exp(-d.y * 1.3) + exp(-dp.y * 0.8) * exp(-d.x * 1.3);
        vec3 col = hsv2rgb(vec3(fract(h.y * 3.0 + u_time * 0.05), 0.35, 1.0));
        glow += col * (core + 0.7 * arms) * tw * min(sqrt(lit) * 2.0, 1.0);
    }
    glow *= u_amount;
    return vec4(glow, peak(glow));
}
