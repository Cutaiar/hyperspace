// The trigger module built from code, in metres: the housing, the blade on its pivot with the arc
// rack on its back, the geared wheel the rack drives, the worm wheel on the same shaft, the worm on
// the motor's shaft, the motor, the board with the position sensor, and a fingertip on the face.
// update(s) poses it all from one solve() — nothing here is keyframed.
import * as THREE from 'three';
import {RoundedBoxGeometry} from 'three/addons/geometries/RoundedBoxGeometry.js';
import {clamp01, M, P} from './trigger.js';

const V3 = THREE.Vector3;

/** A spur gear in the y–z plane, turning about x. */
function gearGeo(teeth, rp, width, holeR = 0) {
  const ra = rp * 1.085, rr = rp * 0.9;
  const sh = new THREE.Shape();
  for (let i = 0; i < teeth; i++) {
    const a0 = (i / teeth) * Math.PI * 2, da = (Math.PI * 2) / teeth;
    const pts = [[rr, a0], [rr, a0 + da * 0.16], [ra, a0 + da * 0.33], [ra, a0 + da * 0.62], [rr, a0 + da * 0.79]];
    pts.forEach(([r, a], k) => (i === 0 && k === 0 ? sh.moveTo(r * Math.cos(a), r * Math.sin(a)) : sh.lineTo(r * Math.cos(a), r * Math.sin(a))));
  }
  sh.closePath();
  if (holeR) {
    const h = new THREE.Path();
    h.absarc(0, 0, holeR, 0, Math.PI * 2, true);
    sh.holes.push(h);
  }
  const g = new THREE.ExtrudeGeometry(sh, {depth: width, bevelEnabled: true, bevelThickness: 0.0003, bevelSize: 0.00025, bevelSegments: 1, curveSegments: 4});
  g.translate(0, 0, -width / 2);
  g.rotateY(Math.PI / 2);     // shape plane y–z, axis along x
  return g;
}
/** A single-start worm: a helical ridge lathed along z. */
function wormGeo() {
  const turns = 7, seg = 160, pts = [];
  for (let i = 0; i <= seg; i++) {
    const u = i / seg, a = u * turns * Math.PI * 2;
    pts.push(new V3(Math.cos(a) * M.wormR * 0.98, Math.sin(a) * M.wormR * 0.98, (u - 0.5) * M.wormLen));
  }
  const g = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 170, M.wormR * 0.33, 7, false);
  return g;
}
/** The arc rack on the blade's back: teeth on a circle of radius rackR about the pivot. */
function rackGeo() {
  const sh = new THREE.Shape();
  const R = M.rackR, span = M.thetaMax * 2.6, n = 13;
  // shape x becomes world z, shape y stays y: the teeth face down-and-aft, toward the gear's axis
  const at = (r, a) => [-Math.sin(a) * r, -Math.cos(a) * r];
  const a0 = Math.PI / 4 - span / 2;
  sh.moveTo(...at(R * 0.86, a0));
  for (let i = 0; i < n; i++) {
    const a = a0 + (i / n) * span, da = span / n;
    sh.lineTo(...at(R * 0.86, a));
    sh.lineTo(...at(R, a + da * 0.28));
    sh.lineTo(...at(R, a + da * 0.62));
    sh.lineTo(...at(R * 0.86, a + da * 0.9));
  }
  sh.lineTo(...at(R * 0.7, a0 + span));
  sh.lineTo(...at(R * 0.7, a0));
  sh.closePath();
  const g = new THREE.ExtrudeGeometry(sh, {depth: M.bladeW * 0.62, bevelEnabled: false, curveSegments: 2});
  g.translate(0, 0, -M.bladeW * 0.31);
  g.rotateY(-Math.PI / 2);
  return g;
}
/** The blade: a paddle hanging from the pivot, its face dished where the finger sits. */
function bladeGeo() {
  const sh = new THREE.Shape();
  const L = M.bladeLen, t = M.bladeTh;
  // y–z section: down from the pivot, the face bowing toward the finger (+z)
  sh.moveTo(0.003, -0.001);
  sh.lineTo(0.003 + t, 0.0005);
  sh.bezierCurveTo(0.0062 + t, -L * 0.42, 0.0050 + t, -L * 0.78, 0.0010, -L);
  sh.lineTo(-0.0030, -L + 0.0015);
  sh.bezierCurveTo(0.0026, -L * 0.78, 0.0038, -L * 0.42, -0.0006, -0.0015);
  sh.closePath();
  const g = new THREE.ExtrudeGeometry(sh, {depth: M.bladeW, bevelEnabled: true, bevelThickness: 0.0008, bevelSize: 0.0009, bevelSegments: 2, curveSegments: 20});
  g.translate(0, 0, -M.bladeW / 2);
  g.rotateY(-Math.PI / 2);     // shape x is +z, toward the finger; the extrude depth is the blade's width
  return g;
}
/** The finger, as a drawing shows one: an arrow onto the pad. */
function fingerArrow(mat, add) {
  const g = new THREE.Group();
  const shaft = add(g, new THREE.CylinderGeometry(0.0011, 0.0011, 0.016, 14), mat, false);
  shaft.rotation.x = Math.PI / 2;
  shaft.position.z = 0.0105;
  const head = add(g, new THREE.ConeGeometry(0.0029, 0.0062, 20), mat, false);
  head.rotation.x = -Math.PI / 2;
  head.position.z = 0.0022;
  return g;
}

export function buildModule() {
  const MAT = {
    shell: new THREE.MeshPhysicalMaterial({color: '#2b2f36', roughness: 0.46, metalness: 0.05, clearcoat: 0.3, clearcoatRoughness: 0.5}),
    blade: new THREE.MeshPhysicalMaterial({color: '#3a3f47', roughness: 0.42, metalness: 0.06, clearcoat: 0.45, clearcoatRoughness: 0.35}),
    grip: new THREE.MeshStandardMaterial({color: '#23262b', roughness: 0.85}),
    steel: new THREE.MeshStandardMaterial({color: '#c6cad0', roughness: 0.3, metalness: 1, envMapIntensity: 0.5}),
    brass: new THREE.MeshStandardMaterial({color: '#b59152', roughness: 0.34, metalness: 0.92, envMapIntensity: 0.5}),
    nylon: new THREE.MeshPhysicalMaterial({color: '#e7e3da', roughness: 0.52, metalness: 0, clearcoat: 0.2}),
    can: new THREE.MeshStandardMaterial({color: '#aeb4bc', roughness: 0.34, metalness: 0.9, envMapIntensity: 0.5}),
    board: new THREE.MeshStandardMaterial({color: '#1d4a3a', roughness: 0.68, metalness: 0.05}),
    copper: new THREE.MeshStandardMaterial({color: '#c08a4a', roughness: 0.4, metalness: 0.8}),
    skin: new THREE.MeshStandardMaterial({color: '#23201c', roughness: 0.5, metalness: 0.1}),
    hot: new THREE.MeshStandardMaterial({color: '#e3562a', roughness: 0.5, emissive: '#e3562a', emissiveIntensity: 0}),
  };
  const all = [];
  const add = (parent, geo, mat, cast = true) => {
    const m = new THREE.Mesh(geo, mat);
    m.castShadow = cast;
    m.receiveShadow = true;
    parent.add(m);
    all.push(m);
    return m;
  };
  const root = new THREE.Group();

  // ---------------------------------------------------------- housing (x-ray and section reach this)
  const shellG = new THREE.Group();
  root.add(shellG);
  const [hw, hh, hd] = M.housing;
  const SHELL_Y = -0.019, SHELL_Z = -0.0225;
  const shell = add(shellG, new RoundedBoxGeometry(hw, hh, hd, 4, 0.0024), MAT.shell);
  shell.position.set(0, SHELL_Y, SHELL_Z);
  const lip = add(shellG, new RoundedBoxGeometry(hw * 1.05, 0.0045, 0.007, 3, 0.0016), MAT.shell);
  lip.position.set(0, -0.0025, -0.0075);
  for (const s of [-1, 1]) {
    const boss = add(shellG, new THREE.CylinderGeometry(0.0022, 0.0022, 0.0035, 14), MAT.shell);
    boss.position.set(s * (hw / 2 + 0.0014), SHELL_Y - hh / 2 + 0.004, SHELL_Z + 0.009);
    boss.rotation.z = Math.PI / 2;
  }

  // ---------------------------------------------------------- the blade, its rack, the pivot and the sensor
  const blade = new THREE.Group();
  root.add(blade);
  add(blade, bladeGeo(), MAT.blade);
  const PAD = {y: -M.bladeLen * 0.64, z: 0.0098};
  const face = add(blade, new RoundedBoxGeometry(M.bladeW * 0.82, 0.015, 0.0034, 3, 0.0012), MAT.grip);
  face.position.set(0, PAD.y, PAD.z);
  add(blade, rackGeo(), MAT.nylon);
  const pin = add(blade, new THREE.CylinderGeometry(0.0016, 0.0016, M.bladeW + 0.0035, 16), MAT.steel);
  pin.rotation.z = Math.PI / 2;
  // the return spring: a coil about the pivot
  {
    const pts = [];
    for (let i = 0; i <= 90; i++) {
      const a = (i / 90) * Math.PI * 5;
      pts.push(new V3(-(M.bladeW / 2 + 0.0008) - (i / 90) * 0.0026, Math.sin(a) * 0.0028, Math.cos(a) * 0.0028));
    }
    add(blade, new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 100, 0.00035, 5, false), MAT.steel);
  }
  // the potentiometer at the pivot: a disc on the board, its wiper turning with the blade
  const pot = new THREE.Group();
  pot.position.set(-(M.bladeW / 2 + 0.0022), 0, 0);
  root.add(pot);
  const potBody = add(pot, new THREE.CylinderGeometry(M.potR * 0.82, M.potR * 0.82, 0.0014, 24), MAT.nylon);
  potBody.rotation.z = Math.PI / 2;
  const wiper = add(pot, new THREE.BoxGeometry(0.0009, M.potR * 1.5, 0.0011), MAT.copper);
  wiper.position.set(-0.0011, -M.potR * 0.55, 0);

  // ---------------------------------------------------------- the train: output gear, worm wheel, worm, motor
  const train = new THREE.Group();
  root.add(train);
  const gearShaft = new THREE.Group();
  gearShaft.position.fromArray(P.gear);
  train.add(gearShaft);
  const X_PINION = -0.0042, X_WORM = 0.0042;
  const pinion = add(gearShaft, gearGeo(14, M.gearR, 0.0055, 0.0011), MAT.nylon);
  pinion.position.x = X_PINION;
  const wheel = add(gearShaft, gearGeo(M.wheelTeeth, M.wheelR, 0.0030, 0.0011), MAT.brass);
  wheel.position.x = X_WORM;
  const shaft = add(gearShaft, new THREE.CylinderGeometry(0.0011, 0.0011, 0.019, 14), MAT.steel);
  shaft.rotation.z = Math.PI / 2;

  const wormG = new THREE.Group();
  wormG.position.fromArray(P.worm);
  wormG.position.x = X_WORM;                       // on the worm wheel's plane
  train.add(wormG);
  const core = add(wormG, new THREE.CylinderGeometry(M.wormR * 0.62, M.wormR * 0.62, M.wormLen, 18), MAT.steel);
  core.rotation.x = Math.PI / 2;
  add(wormG, wormGeo(), MAT.steel);

  const motor = new THREE.Group();
  motor.position.fromArray(P.motor);
  motor.position.x = X_WORM;
  train.add(motor);
  const can = add(motor, new THREE.CylinderGeometry(M.motorR, M.motorR, M.motorLen, 28), MAT.can);
  can.rotation.x = Math.PI / 2;
  for (const z of [-M.motorLen / 2 + 0.0012, M.motorLen / 2 - 0.0012]) {
    const rib = add(motor, new THREE.CylinderGeometry(M.motorR * 1.06, M.motorR * 1.06, 0.0008, 28), MAT.steel);
    rib.rotation.x = Math.PI / 2;
    rib.position.z = z;
  }
  const spindle = add(motor, new THREE.CylinderGeometry(0.0006, 0.0006, 0.005, 10), MAT.steel);
  spindle.rotation.x = Math.PI / 2;
  spindle.position.z = M.motorLen / 2 + 0.002;
  // the two leads, red and black, out of the back
  for (const [s, col] of [[-1, '#c7372b'], ['1', '#1b1d21']]) {
    const x = Number(s) * 0.0014;
    const pts = [new V3(x, 0, -M.motorLen / 2), new V3(x, -0.002, -M.motorLen / 2 - 0.004), new V3(x * 2.4, -0.004, -M.motorLen / 2 - 0.009)];
    add(motor, new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 24, 0.0004, 6, false), new THREE.MeshStandardMaterial({color: col, roughness: 0.75}));
  }

  // ---------------------------------------------------------- the module board, under the train
  const board = new THREE.Group();
  root.add(board);
  const BX = M.housing[0] / 2 - 0.0016;
  const pcb = add(board, new THREE.BoxGeometry(0.0016, 0.017, 0.025), MAT.board);
  pcb.position.set(BX, -0.018, -0.019);
  for (let i = 0; i < 5; i++) {
    const c = add(board, new THREE.BoxGeometry(0.0007, 0.0013, 0.0022), MAT.grip);
    c.position.set(BX - 0.0012, -0.012 - (i % 3) * 0.0038, -0.012 - Math.floor(i / 3) * 0.011);
  }
  // the ribbon out of the module
  {
    const pts = [new V3(BX, -0.0255, -0.030), new V3(BX, -0.030, -0.040), new V3(BX - 0.002, -0.036, -0.050)];
    const g = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 26, 0.0009, 4, false);
    g.scale(0.3, 1, 1);
    add(board, g, MAT.copper);
  }

  // ---------------------------------------------------------- the finger
  const finger = new THREE.Group();
  root.add(finger);
  finger.add(fingerArrow(MAT.skin, (p2, geo, mat, cast) => add(p2 === undefined ? finger : p2, geo, mat, cast)));

  // ---------------------------------------------------------- torque: the accent, on the part doing the work
  const arrow = new THREE.Group();
  arrow.position.fromArray(P.gear);
  root.add(arrow);
  {
    const r = M.gearR * 2.2, pts = [];
    for (let i = 0; i <= 28; i++) {
      const a = -0.9 + (i / 28) * 2.5;
      pts.push(new V3(0.0092, Math.sin(a) * r, Math.cos(a) * r));
    }
    add(arrow, new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 30, 0.0006, 6, false), MAT.hot, false);
    const head = add(arrow, new THREE.ConeGeometry(0.0017, 0.0042, 14), MAT.hot, false);
    const a = 1.6;
    head.position.set(0.0092, Math.sin(a) * r, Math.cos(a) * r);
    head.rotation.x = -a + Math.PI / 2;
  }
  arrow.visible = false;

  // ---------------------------------------------------------- display modes
  const CLIP = new THREE.Plane(new V3(1, 0, 0), 0);
  const GLASS = [MAT.shell, MAT.board];
  let xrayNow = -1, sectionNow = null;
  const setXray = (k) => {
    if (Math.abs(k - xrayNow) < 1e-3) return;
    xrayNow = k;
    for (const m of GLASS) {
      m.transparent = k > 0.002;
      m.opacity = 1 - 0.84 * k;
      m.depthWrite = k < 0.5;
      m.needsUpdate = true;
    }

    MAT.skin.transparent = k > 0.002;
  };
  const setSection = (on) => {
    if (on === sectionNow) return;
    sectionNow = on;
    for (const m of GLASS) {
      m.clippingPlanes = on ? [CLIP] : null;
      m.side = on ? THREE.DoubleSide : THREE.FrontSide;
      m.needsUpdate = true;
    }
  };
  setSection(false);

  /** s: one solve(), plus xray 0..1, section, explode 0..1, torqueGlow 0..1 */
  const update = (s, {xray = 0, section = false, explode = 0} = {}) => {
    setXray(xray);
    setSection(section);
    const e = explode;
    blade.rotation.x = s.theta;
    blade.position.set(0, 0, e * 0.016);
    pot.rotation.x = s.theta;
    pot.position.set(-(M.bladeW / 2 + 0.0022) - e * 0.014, 0, e * 0.016);
    shellG.position.set(0, -e * 0.004, -e * 0.03);
    gearShaft.rotation.x = s.gearA;
    wormG.rotation.z = s.motorA;
    motor.rotation.z = s.motorA;
    train.position.set(0, -e * 0.012, 0);
    motor.position.z = P.motor[2] - e * 0.022;
    board.position.set(e * 0.016, 0, 0);
    // the finger rides the blade's face
    const fy = -M.bladeLen * 0.64, fz = 0.0098 + 0.0017 + 0.0129;   // the pad, its face, then half a fingertip
    finger.position.set(0, fy + 0.0019, fz - 0.0092);
    finger.position.applyAxisAngle(new V3(1, 0, 0), s.theta * 0.92);
    finger.rotation.x = s.theta * 0.92;
    finger.scale.setScalar(0.85 + 0.3 * clamp01(s.demand ?? 0));
    // the accent marks the part doing the work: the torque the motor is holding
    const tq = s.torque;
    MAT.hot.emissiveIntensity = tq * 0.9;
    arrow.visible = tq > 0.04;
    arrow.scale.setScalar(0.55 + 0.45 * tq);
    arrow.rotation.x = s.gearA * 0.25;
    MAT.can.emissive = new THREE.Color('#e3562a');
    MAT.can.emissiveIntensity = tq * 0.1;
    MAT.brass.emissive = new THREE.Color('#e3562a');
    MAT.brass.emissiveIntensity = tq * 0.2;
  };
  update({theta: 0, gearA: 0, motorA: 0, torque: 0});
  return {root, update, MAT, all, CLIP, parts: {blade, shellG, train, motor, wormG, gearShaft, pot, finger, board}};
}
