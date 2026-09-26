// @label Plasma
// @order 5
// @blend screen
// @speed 0.5
// @tip A generator, not a filter: a field of summed sines through a cycling palette,
// @tip drawn under the scene (screen) — it runs with every shape switched off. Placed
// @tip first, the warps after it bend it too.

uniform float u_level;   // @param 0 1 0.35 "Level" Brightness of the field.
uniform float u_scale;   // @param 0.5 20 4 log "Scale" Waves across the frame's height.
uniform float u_fold;    // @param 0 3 1 "Fold" Domain warp: each wave bends the next, from ribbons to marbling.
uniform float u_bands;   // @param 0.2 4 1 log "Bands" Palette cycles across the field's range: high is contour stripes.

vec4 effect(vec2 uv) {
    vec2 p = centred(uv) * u_scale;
    float t = u_phase;
    for (int k = 1; k <= 3; k++) {       // each octave displaced by the last
        float fk = float(k);
        p += u_fold / fk * vec2(sin(p.y * fk + t * 1.3 + fk), cos(p.x * fk - t * 0.9 + fk * 2.0));
    }
    float v = sin(p.x + t) + sin(p.y * 1.3 - t * 0.7) + sin(length(p) * 1.7 + t * 1.1);
    vec3 c = pal(v * 0.25 * u_bands + t * 0.05, vec3(0.5), vec3(0.5),
                 vec3(1.0, 1.0, 1.0), vec3(0.0, 0.33, 0.67));
    c *= u_level;
    return vec4(c, peak(c));
}
