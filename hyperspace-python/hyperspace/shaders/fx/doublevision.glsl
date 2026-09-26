// @label Double vision
// @order 30
// @blend mix
// @tip Noita's drunk double vision (drugged_doublevision_amount): a ghost of the frame
// @tip blended over it, offset along a slow circle.

uniform float u_amount;  // @param 0 12 1 "Amount" The ghost's offset: 1 is Noita's drunk stage, half a percent of the frame.
uniform float u_ghost;   // @param 0 1 0.5 "Ghost" The ghost's weight; Noita blends half and half.
uniform int u_copies;    // @param 1 4 1 "Copies" Ghosts spaced around the circle.

vec4 effect(vec2 uv) {
    vec4 c = src(uv);
    vec4 g = vec4(0.0);
    for (int k = 0; k < u_copies; k++) {
        float a = u_phase * 0.5 + float(k) * TAU / float(u_copies);
        g += src(uv + 0.005 * vec2(cos(a), sin(a)) * u_amount);
    }
    return mix(c, g / float(u_copies), u_ghost);
}
