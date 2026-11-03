// The DualSense adaptive trigger as numbers: the mechanism's kinematics in metres, and the
// protocol that drives it, byte for byte. No three.js in here.
//
// MECHANISM — a schematic reconstruction. Teardowns agree on the parts and their arrangement
// (a DC motor, a worm on its shaft, a gear train, a geared wheel the trigger blade contacts, and
// a potentiometer on the module board reading where the blade is); Sony publishes no dimensions,
// so every length below is this model's own, chosen to match the module in the teardown photos.
// The one thing the arrangement explains for free: a worm drive is self-locking, so holding the
// motor holds the blade. That is what a "wall" is.
//
// PROTOCOL — exact. Eleven bytes, mode in [0], parameters in [1..10], from
// docs/plans/assets/42-controllers/sony-hid.md §6: Off 0x05, Feedback 0x21 (a 10-bit zone mask
// and 3 bits of force per zone), Weapon 0x25, Vibration 0x26 (the same packing plus Hz in [9]).

export const D2R = Math.PI / 180;
export const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
export const clamp01 = (x) => clamp(x || 0, 0, 1);

// ------------------------------------------------------------ the module, in metres (mm in comments)
export const M = {
  thetaMax: 15 * D2R,   // the blade's full sweep
  bladeLen: 0.034,      // 34 mm, pivot to tip
  bladeW: 0.011,        // 11 mm across
  bladeTh: 0.0055,      // 5.5 mm thick
  rackR: 0.0135,        // 13.5 mm: the arc rack on the blade's back, about the pivot
  gearR: 0.0042,        // 4.2 mm pitch radius, the pinion the rack drives
  wheelR: 0.0070,        // 14 mm pitch diameter, 20 teeth — the worm wheel, bigger than the pinion
  wheelTeeth: 20,
  wormR: 0.0016,        // 3.2 mm, single start: 20:1 into the wheel, and self-locking
  wormLen: 0.009,
  motorR: 0.003,        // a 6 mm can, 16 mm long
  motorLen: 0.016,
  potR: 0.0035,         // the position sensor at the pivot
  housing: [0.023, 0.030, 0.034],   // sized to hold the train: see P below
};
// Where each axis sits in the module frame: x across, y up, z toward the finger. The blade hangs
// from the pivot at the origin and swings aft. Every centre distance is the sum of two pitch radii,
// so the teeth mesh instead of passing through each other:
//   rack (13.5) + gear (5.8) = 19.3 mm from the pivot, down and aft at 45°
//   wheel (5.0) + worm (1.6) = 6.6 mm below the gear shaft
const D_GEAR = (M.rackR + M.gearR) / Math.SQRT2;
export const P = {
  pivot: [0, 0, 0],
  gear: [0, -D_GEAR, -D_GEAR],                             // the wheel the blade's rack drives
  wheel: [0, -D_GEAR, -D_GEAR],                            // the worm wheel shares its shaft
  worm: [0, -D_GEAR - (M.wheelR + M.wormR), -D_GEAR],      // under it, axis along z, single start
  motor: [0, -D_GEAR - (M.wheelR + M.wormR), -D_GEAR - M.wormLen / 2 - M.motorLen / 2 - 0.001],
};
export const RATIO = M.rackR / M.gearR;        // blade radians → output-gear radians
export const WORM_RATIO = M.wheelTeeth;        // gear radians → motor radians

// ------------------------------------------------------------ the protocol (exact)
export const ZONES = 10;
export const T_OFF = 0x05, T_FEEDBACK = 0x21, T_WEAPON = 0x25, T_VIBRATION = 0x26;
export const MODE_NAME = {[T_OFF]: 'Off', [T_FEEDBACK]: 'Feedback', [T_WEAPON]: 'Weapon', [T_VIBRATION]: 'Vibration'};
// the ones the driver refuses: unofficial, legacy, and the two that corrupt the trigger
export const REFUSED = [['0x22', 'Bow'], ['0x23', 'Galloping'], ['0x27', 'Machine'], ['0xFC-FE', 'debug']];
export const zoneOf = (u) => clamp(Math.round(clamp01(u) * 9), 0, 9);
export const zoneU = (z) => z / 9;
export const flat = (from, force) => Array.from({length: ZONES}, (_, z) => (z >= from ? force : 0));

/** A descriptor's 11 bytes, packed as the firmware takes them. */
export function packet(d) {
  const b = new Uint8Array(11);
  if (d.mode === 'weapon') {
    const s = clamp(d.start | 0, 2, 7), e = clamp(Math.max(d.end | 0, s + 1), s + 1, 8);
    b[0] = T_WEAPON;
    b[1] = ((1 << s) | (1 << e)) & 0xff;
    b[2] = (((1 << s) | (1 << e)) >> 8) & 0xff;
    b[3] = clamp(Math.round(d.strength), 1, 8) - 1;
    return b;
  }
  if (d.mode === 'feedback' || d.mode === 'vibration') {
    let mask = 0, forces = 0;
    (d.zones || []).forEach((v, z) => {
      const f = clamp(Math.round(v), 0, 8);
      if (f > 0) { mask |= 1 << z; forces += (f - 1) * Math.pow(2, 3 * z); }
    });
    if (!mask) { b[0] = T_OFF; return b; }
    b[0] = d.mode === 'vibration' ? T_VIBRATION : T_FEEDBACK;
    b[1] = mask & 0xff; b[2] = (mask >> 8) & 0xff;
    const f = forces >>> 0;
    b[3] = f & 0xff; b[4] = (f >>> 8) & 0xff; b[5] = (f >>> 16) & 0xff; b[6] = (f >>> 24) & 0xff;
    if (d.mode === 'vibration') b[9] = clamp(Math.round(d.freq || 1), 1, 255);
    return b;
  }
  b[0] = T_OFF;
  return b;
}
/** The zone forces a packet asks for, read back out of the bytes (what the plot draws). */
export function unpack(b) {
  if (b[0] === T_WEAPON) {
    const mask = b[1] | (b[2] << 8), on = [];
    for (let z = 0; z < ZONES; z++) if (mask & (1 << z)) on.push(z);
    const lvl = (b[3] & 7) + 1;
    return Array.from({length: ZONES}, (_, z) => (on.length && z >= on[0] && z <= on[on.length - 1] ? lvl : 0));
  }
  if (b[0] !== T_FEEDBACK && b[0] !== T_VIBRATION) return new Array(ZONES).fill(0);
  const mask = b[1] | (b[2] << 8), f = (b[3] | (b[4] << 8) | (b[5] << 16) | (b[6] << 24)) >>> 0;
  return Array.from({length: ZONES}, (_, z) => (mask & (1 << z) ? ((Math.floor(f / Math.pow(2, 3 * z))) & 7) + 1 : 0));
}

// ------------------------------------------------------------ the recipes the page can send
const curve = (shape, from, lo, hi) => Array.from({length: ZONES}, (_, z) => {
  if (z < from) return 0;
  const x = (z - from) / Math.max(1, 9 - from);
  const k = shape === 'in' ? x * x : shape === 'inverse' ? 1 - x : x;
  return clamp(Math.round(lo + (hi - lo) * k), 0, 8);
});
export const RECIPES = {
  free: {name: 'FREE', note: 'Off 0x05 · nothing in the way', make: () => ({mode: 'off'})},
  wall: {name: 'WALL', note: 'Feedback 0x21 · one force from zone 4 down — all the app sends today',
    make: () => ({mode: 'feedback', zones: flat(4, 7)})},
  sniper: {name: 'SNIPER', note: 'Weapon 0x25 · slack, a wall at zone 4, and past zone 6 it gives way',
    make: () => ({mode: 'weapon', start: 4, end: 6, strength: 8})},
  curve: {name: 'CURVE', note: 'Feedback 0x21 multiple position · a brake pedal: soft, then firm',
    make: () => ({mode: 'feedback', zones: curve('in', 1, 1, 8)})},
  detents: {name: 'DETENTS', note: 'Feedback 0x21 · a mask with gaps: notches the finger counts',
    make: () => ({mode: 'feedback', zones: [8, 0, 0, 8, 0, 0, 8, 0, 0, 8]})},
  buzz: {name: 'BUZZ', note: 'Vibration 0x26 · the same motor driving the stop in and out, 45 Hz',
    make: () => ({mode: 'vibration', zones: flat(0, 6), freq: 45})},
  recoil: {name: 'RECOIL', note: 'a wall that fires: cross it and the motor rattles, then the wall is back',
    make: (t, st) => (st.firing ? {mode: 'vibration', zones: flat(3, 8), freq: 90} : {mode: 'feedback', zones: flat(5, 7)}),
    breakAt: 5},
  mass: {name: 'MASS', note: 'the loop, not a shape: the force follows how fast the finger is moving',
    make: (t, st) => ({mode: 'feedback', zones: flat(0, clamp(Math.abs(st.vel) / 2.5 * 8, 0, 8))}),
    loop: true},
};
export const RECIPE_KEYS = Object.keys(RECIPES);

// ------------------------------------------------------------ what the finger actually gets
/** The blade is held by the stop when the zone it is entering pushes harder than the finger.
 *  A worm drive is self-locking, so a force the finger cannot beat is a hard stop, not a spring.
 *  Weapon releases at its end zone: the slack, the wall, and the break. */
export function resolve(demand, zones, mode, grip, weapon) {
  const d = clamp01(demand);
  if (mode === 'weapon' && weapon) {
    const wall = zoneU(weapon.start), brk = zoneU(weapon.end);
    if (d <= wall) return {u: d, blocked: false, broke: false};
    // through the wall only once the finger is past the break: then it gives way at once
    if (d >= brk) return {u: d, blocked: false, broke: true};
    return {u: wall, blocked: weapon.strength >= grip, broke: false};
  }
  let stop = 1;
  for (let z = 0; z < ZONES; z++) {
    if ((zones[z] || 0) >= grip) { stop = zoneU(z); break; }
  }
  return {u: Math.min(d, stop), blocked: d > stop + 1e-4, broke: false};
}

/** One frame of the whole machine, from the finger's demand and the recipe.
 *  `st` carries what the loop recipes need: vel (travel/s) and the recoil's firing flag. */
export function solve({demand = 0, recipe = 'free', t = 0, grip = 6, st = {}} = {}) {
  const R = RECIPES[recipe] || RECIPES.free;
  const desc = R.make(t, {vel: st.vel || 0, firing: !!st.firing}) || {mode: 'off'};
  const bytes = packet(desc);
  const zones = unpack(bytes);
  const weapon = desc.mode === 'weapon' ? desc : null;
  const r = resolve(demand, zones, desc.mode, grip, weapon);
  const u = r.u;
  const z = zoneOf(u);
  const force = desc.mode === 'off' ? 0 : zones[z] || 0;
  // the motor's job: hold the train against the blade (feedback / weapon), or drive it in and out
  const buzzing = desc.mode === 'vibration' && force > 0;
  const buzz = buzzing ? Math.sin(t * 2 * Math.PI * (desc.freq || 1)) * (force / 8) : 0;
  const theta = u * M.thetaMax + buzz * 0.055 * M.thetaMax;
  return {
    desc, bytes, zones, u, demand: clamp01(demand), zone: z, force, buzz, buzzing,
    blocked: r.blocked, broke: r.broke,
    theta,                                   // the blade's angle
    gearA: -theta * RATIO,                   // the wheel the rack drives
    motorA: theta * RATIO * WORM_RATIO,      // and the worm, twenty times round
    torque: clamp01(force / 8),              // what the motor is holding against
    pot: Math.round(u * 255),                // what the module's potentiometer reports: 8 bits
    mode: desc.mode,
    modeByte: bytes[0],
  };
}
