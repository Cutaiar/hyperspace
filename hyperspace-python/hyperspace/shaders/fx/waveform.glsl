// @label Waveform
// @order 13
// @family field
// @speed 1
// @clock u_drift_t drift 4096
// @makes field
// @takes image field
// @tip A waveform laid over a field: its value counted in Waves, then sine, triangle,
// @tip square, saw or noise of it, −1 … 1, drifting on. Wire a Measure in (rings make
// @tip ripples, a line makes rows) and its output into a node that reads a field. Steps
// @tip flattens it into slabs. Whole rounds Waves to a whole number, for a measure that
// @tip comes back on itself (spokes), so the last wave meets the first.

// The second of DISTORTION.md's three questions as a node — `wave()`
// over a field, as wave.glsl does over its own measure, so `measure →
// waveform → combine → displace` is wave.glsl to the bit
uniform float u_waves;  // @param 0.25 64 3 log "Waves" Waves for each unit of the field in (a Measure's frame height, or turn for spokes).
uniform int u_shape;    // @param choice [sine|triangle|square|saw|noise] 0 "Shape" The waveform. Square and saw have an edge; noise is a new random level each wave.
uniform int u_round;    // @param choice [free|whole] 0 "Round" Whole: Waves rounded to a whole number, and noise repeating after that many — for spokes, so the last wave meets the first.
uniform float u_drift;  // @param 0 8 0.5 "Drift" Waves passing a second.
uniform float u_start;  // @param 0 1 0 wrap "Phase" Where in its cycle the wave starts, turns (an LFO's Phase): 0.25 puts a sine's crest where the field is 0.
uniform int u_steps;    // @param 0 16 0 "Steps" Levels each side of rest the wave is flattened to, so a smooth wave becomes slabs. 0 leaves it smooth.

// (Phase is `start`: `u_phase` is every file's clock, and `fx.<n>.phase` the
// position jog)
vec4 effect(vec2 uv) {
    float every = u_round == 1 ? max(floor(u_waves + 0.5), 1.0) : 4096.0;   // where noise repeats
    vec4 f = field_in(uv);
    float x = f.x * (u_round == 1 ? every : u_waves);                      // the field, in waves
    float w = u_shape == 4 ? noise1(x - u_drift_t + u_start, every)
                           : wave(u_shape, x - u_drift_t + u_start);
    // what rides with the value in y and z (a Measure's direction, a cell's
    // size) rides on with the wave
    return vec4(quantise(w, u_steps), f.yz, 0.0);
}
