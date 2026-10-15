// @label Palette
// @order 95
// @blend mix
// @speed 1
// @mix 0
// @tip The last colour pass: every hue is folded onto a slice of the colour wheel you
// @tip choose and move (a triangle wave, so neighbouring hues stay neighbours and there is
// @tip no seam), with saturation and brightness rescaled into a range. Or, in gradient
// @tip mode, the frame's brightness is painted through a ramp of up to four colours.
// @tip Mix 0 (the start) leaves the picture as it was.

uniform int   u_mode;    // @param 0 1 0 "Mode" 0 folds the hues onto the slice; 1 maps brightness through the ramp below.
uniform float u_centre;  // @param 0 360 0 wrap "Centre" Fold: the middle of the slice, degrees (0 red, 120 green, 240 blue).
uniform float u_width;   // @param 0 360 360 "Width" Fold: how wide the slice is, degrees; 0 is one hue, 360 the whole wheel folded onto itself.
uniform float u_sat_lo;  // @param 0 1 0 "Sat low" Fold: where the least saturated colour lands.
uniform float u_sat_hi;  // @param 0 1 1 "Sat high" Fold: where the most saturated colour lands.
uniform float u_val_lo;  // @param 0 1 0 "Val low" Fold: where the darkest pixel lands.
uniform float u_val_hi;  // @param 0 1 1 "Val high" Fold: where the brightest pixel lands.
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
        // triangle wave over the wheel: 0 at red, 1 at cyan, back to 0 at red
        float tri = 1.0 - abs(2.0 * fract(h.x) - 1.0);
        float hue = (u_centre + (tri - 0.5) * u_width) / 360.0;
        rgb = hsv2rgb(vec3(fract(hue), mix(u_sat_lo, u_sat_hi, h.y), mix(u_val_lo, u_val_hi, h.z)));
    } else {
        int n = clamp(u_anchors, 2, 4);
        float x = clamp(luma(c.rgb), 0.0, 1.0) * float(n - 1);
        int i = min(int(floor(x)), n - 2);
        rgb = mix(anchor(i), anchor(i + 1), x - float(i));
    }
    return vec4(rgb, c.a);
}
