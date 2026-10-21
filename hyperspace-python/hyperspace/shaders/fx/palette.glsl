// @label Palette
// @order 95
// @blend mix
// @speed 1
// @mix 0
// @tip Compresses every colour into a slice of the HSV cylinder you set (a hue arc,
// @tip a saturation range, a brightness range), or maps brightness through a ramp.
// @tip Mix 0 leaves the picture alone.

// plan 30 N8 (the owner, 2026-10-20): mode 0 is a colour compression — the
// whole HSV cylinder mapped onto the closed slice hue_from → hue_to (degrees,
// going up the wheel from `from`, through 360 when to < from; from == to is
// one hue, 0 → 360 the whole wheel), sat_from → sat_to and val_from → val_to
// (a linear map, never a clamp: the whole input range lands inside the slice,
// and from > to inverts it). The defaults are the whole cylinder: the identity.
uniform int   u_mode;      // @param choice [compress|gradient] 0 "Mode" Compress maps every colour into the slice below; gradient maps brightness through the ramp.
uniform float u_hue_from;  // @param 0 360 0 "Hue from" Compress: where the slice of the wheel starts, degrees (0 red, 60 yellow, 120 green, 240 blue).
uniform float u_hue_to;    // @param 0 360 360 "Hue to" Compress: where it ends, going up the wheel (through 360 when below from); equal to from is one hue, 0 to 360 the whole wheel.
uniform float u_sat_from;  // @param 0 1 0 "Sat from" Compress: where the least saturated colour lands.
uniform float u_sat_to;    // @param 0 1 1 "Sat to" Compress: where the most saturated colour lands (below from inverts).
uniform float u_val_from;  // @param 0 1 0 "Val from" Compress: where the darkest pixel lands.
uniform float u_val_to;    // @param 0 1 1 "Val to" Compress: where the brightest pixel lands (below from inverts).
uniform int   u_anchors; // @param 2 4 4 "Anchors" Gradient: how many of the four ramp colours are used, dark to light.
uniform float u_a1_hue;  // @param 0 360 0 wrap "A1 hue" Ramp colour 1 (darkest): hue, degrees.
uniform float u_a1_sat;  // @param 0 1 0 "A1 sat" Ramp colour 1: saturation.
uniform float u_a1_val;  // @param 0 1 0 "A1 val" Ramp colour 1: brightness.
uniform float u_a2_hue;  // @param 0 360 0 wrap "A2 hue" Ramp colour 2: hue, degrees.
uniform float u_a2_sat;  // @param 0 1 0 "A2 sat" Ramp colour 2: saturation.
uniform float u_a2_val;  // @param 0 1 0.333 "A2 val" Ramp colour 2: brightness.
uniform float u_a3_hue;  // @param 0 360 0 wrap "A3 hue" Ramp colour 3: hue, degrees.
uniform float u_a3_sat;  // @param 0 1 0 "A3 sat" Ramp colour 3: saturation.
uniform float u_a3_val;  // @param 0 1 0.667 "A3 val" Ramp colour 3: brightness.
uniform float u_a4_hue;  // @param 0 360 0 wrap "A4 hue" Ramp colour 4 (lightest): hue, degrees.
uniform float u_a4_sat;  // @param 0 1 0 "A4 sat" Ramp colour 4: saturation.
uniform float u_a4_val;  // @param 0 1 1 "A4 val" Ramp colour 4: brightness.

vec3 anchor(int i) {
    vec3 h = i == 0 ? vec3(u_a1_hue, u_a1_sat, u_a1_val)
           : i == 1 ? vec3(u_a2_hue, u_a2_sat, u_a2_val)
           : i == 2 ? vec3(u_a3_hue, u_a3_sat, u_a3_val)
           :          vec3(u_a4_hue, u_a4_sat, u_a4_val);
    return hsv2rgb(vec3(fract(h.x / 360.0), h.y, h.z));
}

vec4 effect(vec2 uv) {
    vec4 c = src(uv);
    vec3 rgb;
    if (u_mode == 0) {
        vec3 h = rgb2hsv(c.rgb);
        // the arc, degrees: from up the wheel to to, through 360 when to < from
        float arc = u_hue_to >= u_hue_from ? u_hue_to - u_hue_from : u_hue_to + 360.0 - u_hue_from;
        float centre = u_hue_from + arc * 0.5;
        float width = arc;
        // the fold (plan 24 C6): a triangle wave over the wheel, 0 at red
        // (lands on from), 1 at cyan (lands on to), back to 0 at red — a
        // seamless map of the whole wheel onto the arc. Up to 180° wide it is
        // the old fold to the bit (the D1 goldens hold it)
        float tri = 1.0 - abs(2.0 * fract(h.x) - 1.0);
        if (arc > 180.0) {
            // wider: the climb's peak slides from cyan towards the far red,
            // so at 360 the climb is the whole wheel and the map the identity
            float p = 0.5 + 0.5 * smoothstep(180.0, 360.0, arc);
            float x = fract(h.x);
            tri = x < p ? x / p : (1.0 - x) / max(1.0 - p, 1e-6);
        }
        float hue = (centre + (tri - 0.5) * width) / 360.0;
        rgb = hsv2rgb(vec3(fract(hue), mix(u_sat_from, u_sat_to, h.y), mix(u_val_from, u_val_to, h.z)));
    } else {
        int n = clamp(u_anchors, 2, 4);
        float x = clamp(luma(c.rgb), 0.0, 1.0) * float(n - 1);
        int i = min(int(floor(x)), n - 2);
        rgb = mix(anchor(i), anchor(i + 1), x - float(i));
    }
    // a see-through pixel stays see-through: lifting val_from (or a ramp colour
    // above black) must not light the desktop or a face's empty ground
    if (u_opaque == 0) rgb *= c.a;
    return vec4(rgb, c.a);
}
