// @label Dream
// @order 79
// @family glow and texture
// @blend mix
// @mix 1
// @hook dream
// @tip Deep Dream on whatever picture is wired in: a net's layer pushed into it by a few
// @tip gradient steps a job, on the dream worker's own thread, a job or two late. It
// @tip dreams where its picture is (its alpha: key a picture with black is clear to
// @tip dream only where it is lit) and makes the dreamed picture at its input's size —
// @tip a Resize before it decides the size, so the cost. Hold 1 dreams each picture
// @tip anew; lower, it keeps what it dreamed and dreams it again: deeper, slower to follow.
// @tip Needs the worker: [dream] enabled = true in config.toml (torch).

// The dream node as an effect file with a Python half (`// @hook dream`,
// `hyperspace/dreamhook.py`): the hook reads the picture back when the worker is free,
// hands it over with these knobs, and binds the newest result on unit 2. The file
// returns that result; the effect's own mix and blend lay it on its input, as any effect.
// The layer's names are in their stored order (a save keeps the index): append only.

uniform float u_k;       // @param 0.03 1 1 log "Hold" How much of each new picture a job blends into what the dream holds: 1 dreams each picture anew (no memory), lower keeps what it dreamed and dreams it again — deeper, lingering, slower to follow.
uniform int   u_layer;   // @param choice [conv2_2|conv3_3|conv4_3|inception3b|inception4c|inception4e|conv1_1|conv1_2|conv2_1|conv3_1|conv3_2|conv4_1|conv4_2|conv5_1|conv5_2|conv5_3|conv1|conv2|conv3|inception3a|inception4a|inception4b|inception4d|inception5a|inception5b] 1 "Layer" Which layer of which net it brings out (VGG16 conv…, GoogLeNet conv1–3 and inception…): shallow ones fine dots and edges, middle ones swirls, deep ones blobs and eyes, and slower. A net's first layer loads it, a moment; the rest are then instant.
uniform int   u_steps;   // @param 1 3 2 "Passes" Gradient steps through the net a job: more is deeper and slower.
uniform float u_step;    // @param 0.005 0.06 0.03 "Strength" How hard each step pushes. With Hold below 1, strength × passes is kept at or under 1.5 × Hold (0.5 × Hold where the picture covers everything); the status says when it is held back.
uniform int   u_jitter;  // @param 0 16 8 "Jitter" A random shift each step, pixels, that turns pixel noise into texture.
uniform int   u_octaves; // @param choice [1|2 alt|3 alt] 0 "Scales" The sizes it works at, one a job in turn: more gives larger forms for the same cost.

// set by dreamhook.py each pass, never params
uniform sampler2D u_dream;  // the newest dreamed picture (unit 2), at the input's size
uniform int u_dream_on;     // 1 while one has landed for this instance

vec4 effect(vec2 uv) {
    return u_dream_on != 0 ? texture(u_dream, uv) : src(uv);
}
