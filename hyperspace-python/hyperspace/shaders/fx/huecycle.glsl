// @label Hue cycle
// @order 85
// @blend mix
// @speed 0.25
// @tip Colour cycling: the frame's hues turn around the wheel (Minecraft's wobble turns
// @tip them once a second), in bands across the screen. White has no hue to turn, so
// @tip Paint re-colours by brightness — a wireframe comes out rainbow.

uniform float u_paint;   // @param 0 1 0.7 "Paint" 0 turns the colours the frame has; 1 paints its brightness in the cycling rainbow.
uniform float u_spread;  // @param 0 4 0.8 "Spread" Hue bands across the frame: 0 is one colour at a time.
uniform float u_rings;   // @param 0 1 0.5 "Rings" The bands' shape: 0 diagonal stripes, 1 rings from the centre.
uniform float u_sat;     // @param 0 2 1 "Saturation" Of the result; 0 greyscale.

vec4 effect(vec2 uv) {
    vec4 c = src(uv);
    vec2 p = centred(uv);
    float band = mix(p.x + p.y, length(p) * 2.0, u_rings);
    float h = u_phase + u_spread * band;          // turns
    vec3 turned = hue_rotate(c.rgb, h * TAU);
    vec3 painted = peak(c.rgb) * hsv2rgb(vec3(fract(h), 0.85, 1.0));
    vec3 rgb = mix(turned, painted, u_paint);
    float y = luma(rgb);
    rgb = max(mix(vec3(y), rgb, u_sat), 0.0);
    return vec4(rgb, c.a);
}
