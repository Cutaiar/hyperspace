// @label Colour
// @order 2
// @family generators
// @blend mix
// @speed 1
// @takes image none
// @volume u_hue u_saturation u_value "HSV"
// @clock u_spin_t spin 1
// @tip A generator: one flat colour, a place on the HSV cylinder — Hue the way round,
// @tip Saturation out from the grey middle, Value up from black. It takes no input, so it
// @tip runs wired straight into an output, a composite or an effect's aux. Spin turns the
// @tip hue round the cylinder on its own; every knob takes an LFO, a hand or a band.

uniform float u_hue;         // @param 0 1 0 wrap "Hue" The way round the colour wheel, in turns: 0 red, 1/3 green, 2/3 blue, and round to red again.
uniform float u_saturation;  // @param 0 1 1 unipolar "Saturation" Out from the middle: 0 a grey, 1 the full colour.
uniform float u_value;       // @param 0 1 1 unipolar "Value" Up from black: 0 black, 1 the brightest the colour goes.
uniform float u_spin;        // @param -2 2 0 bipolar "Spin" Turns of the hue a second, either way; 0 holds it where Hue puts it.

// plan 80's rule (`graph.runs_unfed`): no input port, so it is built and drawn with
// nothing wired in. The spin is a clock (`u_spin_t`, turns, kept in [0, 1)), so a
// Spin step changes the rate only, never where the hue is
vec4 effect(vec2 uv) {
    return vec4(hsv(fract(u_hue + u_spin_t), u_saturation, u_value), 1.0);
}
