// @label Oil slick
// @order 72
// @blend mix
// @speed 0.15
// @tip Thin-film iridescence: the frame seen through a film of oil or soap a few
// @tip wavelengths thick, crawling over it. Each colour cancels itself at its own
// @tip depth, so a step in thickness walks the whole spectrum — the sheen on a bubble,
// @tip a puddle, the rim of a prism. The film tints the light through it, so black
// @tip stays black and the shape keeps its form; Glow is what it throws back instead,
// @tip a rainbow haze reaching Halo px past whatever is lit. Rings thicken it toward
// @tip the edge for the bands around a bright middle, Ground lays it over the black too.
// @clock u_drift_t drift*scale

uniform float u_amount; // @param 0 1 0.8 amount "Amount" How deeply the film tints what shines through it. 0 leaves the frame's own colours.
uniform float u_glow;   // @param 0 2 0.35 "Glow" What the film throws back on its own: a rainbow haze over and around the lit pixels.
uniform float u_halo;   // @param 0 48 18 "Halo" How far past the shape that haze reaches, px — a wireframe is a pixel wide.
uniform float u_scale;  // @param 0.5 24 3 log "Scale" Swirls of the film across the frame's height.
uniform float u_bands;  // @param 0.25 12 1.5 log "Bands" Wavelengths the thickness swings through — rainbow repeats per swirl.
uniform float u_rings;  // @param 0 8 1.5 "Rings" Thickness added with distance from the centre: bands around the middle.
uniform float u_drift;  // @param 0 4 1 "Drift" How fast the film crawls, swirls a second; a step changes the rate, never where the film is.
uniform float u_ground; // @param 0 1 0 "Ground" How much of the haze lands where the frame is black; 1 is the film across the whole frame.

// The colour a film `d` wavelengths thick throws back: each wavelength
// interferes with itself on its own period (red 650 nm, green 550, blue 440 —
// here as periods against red), so a step in d walks the spectrum. None of
// them ever goes right out, because a film under a broad light reflects some
// of all of them — which is why a slick is pearl, never a hue wheel's primaries.
vec3 film(float d) {
    return 0.7 + 0.3 * cos(TAU * d * vec3(1.0, 1.18, 1.48));
}

// How much light reaches this pixel from within `r` px: the brightest
// neighbour, dimmed by how far away it is. `reach` takes one ring at its
// full value, which on a wireframe lays twelve hard copies of every line at
// a wide halo; here the ring is turned and its radii nudged by a per-pixel
// hash, as zoomblur dithers its streak, so what is left is a soft grain
// rather than ghosts of the picture.
float haze(vec2 uv, float r) {
    float m = peak(texture(u_src, uv).rgb);
    if (r <= 0.0) return m;
    vec2 j = hash22(uv * u_res);
    for (int k = 0; k < 12; k++) {
        float a = (float(k) + j.x) * (TAU / 12.0);
        vec2 dir = vec2(cos(a), sin(a)) * (r / u_res);
        for (int i = 0; i < 3; i++) {
            float t = (float(i) + j.y) / 3.0;
            m = max(m, (1.0 - 0.8 * t) * peak(texture(u_src, uv + dir * t).rgb));
        }
    }
    return m;
}

vec4 effect(vec2 uv) {
    vec4 c = src(uv);
    vec2 p = centred(uv);
    vec2 pos = p * u_scale;
    // the film is dragged about by a slow current rather than scrolled
    vec2 flow = perlin2(pos * 0.45 + vec2(u_drift_t * 0.25, u_drift_t * -0.17));
    float d = (perlin(pos + flow * 2.0) * 2.0 + perlin(pos * 2.3 - flow) * 0.8) * u_bands
            + length(p) * 2.0 * u_rings;
    vec3 f = film(d);
    // what comes through the film is tinted by it: a see-through pixel is
    // still see-through, so the shape keeps its own shape
    vec3 col = c.rgb * mix(vec3(1.0), f / 0.7, u_amount);
    // and what it throws back instead is the rest of the light — the
    // complement of what it let through, which is where the deep colour is
    col += ((1.0 - f) / 0.3) * (u_glow * max(haze(uv, u_halo), u_ground));
    return vec4(max(col, 0.0), c.a);
}
