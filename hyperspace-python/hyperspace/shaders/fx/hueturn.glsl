// @label Hue turn
// @order 85
// @blend mix
// @speed 0.1
// @tip Turns the frame's hues round the wheel, by Turn and by its clock (Speed), in
// @tip YIQ so brightness holds. White has no hue to turn, so Paint re-colours by
// @tip brightness — a wireframe comes out rainbow. Wire a field into Turn to band
// @tip the hues across the frame (Line, Rings): what Hue cycle's Spread was.

// Hue cycle without its bands: the bands are field nodes (a diagonal mixed
// with rings, × Spread) wired into Turn at a depth of 360 (degrees a turn).
// One op, because Paint mixes two results of the same input.
// At Turn 0 with the field wired as `graphmigrate.hue_turns` wires it, the
// picture is Hue cycle's to the GPU's rounding (`tests/test_hue_turn.py`).

uniform float u_turn;    // @param 0 360 0 wrap "Turn" Degrees round the wheel, added to the clock's turning. Wire a field here to band the hues across the frame.
uniform float u_paint;   // @param 0 1 0.7 "Paint" 0 turns the colours the frame has; 1 paints its brightness in the turning hue.
uniform float u_sat;     // @param 0 2 1 "Saturation" Of the result; 0 greyscale, 2 twice as vivid.

vec4 effect(vec2 uv) {
    vec4 c = src(uv);
    float h = u_phase + u_turn / 360.0;          // turns
    vec3 turned = hue_rotate(c.rgb, h * TAU);
    vec3 painted = peak(c.rgb) * hsv2rgb(vec3(fract(h), 0.85, 1.0));
    vec3 rgb = mix(turned, painted, u_paint);
    float y = luma(rgb);
    rgb = max(mix(vec3(y), rgb, u_sat), 0.0);
    return vec4(rgb, c.a);
}
