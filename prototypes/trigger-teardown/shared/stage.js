// The module's studio: a pale paper ground with a faint grid, three soft boxes in the environment,
// one sun, GTAO. frame(state, cam) poses the module and draws one frame.
import * as THREE from 'three';
import {EffectComposer} from 'three/addons/postprocessing/EffectComposer.js';
import {GTAOPass} from 'three/addons/postprocessing/GTAOPass.js';
import {OutputPass} from 'three/addons/postprocessing/OutputPass.js';
import {Pass} from 'three/addons/postprocessing/Pass.js';
import {RenderPass} from 'three/addons/postprocessing/RenderPass.js';
import {buildModule} from './module3d.js';

const V3 = THREE.Vector3;
export const COL = {bg: '#edeae4', ground: '#e6e2da', grid: '#d2ccc0', shadow: '#4a4238', or: '#e3562a'};
export const GROUND_Y = -0.046;

const G_VERT = /* glsl */ `varying vec3 vW; void main(){ vec4 w = modelMatrix * vec4(position,1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`;
const G_FRAG = /* glsl */ `uniform vec3 uG; uniform vec3 uL; uniform vec3 uBg; uniform vec3 uC; varying vec3 vW;
  void main(){
    // a 5 mm graph grid, every fifth line darker
    vec2 p = vW.xz * 200.0;
    vec2 g = abs(fract(p) - 0.5) / fwidth(p);
    float fine = 1.0 - min(min(g.x, g.y), 1.0);
    vec2 p5 = vW.xz * 40.0;
    vec2 g5 = abs(fract(p5) - 0.5) / fwidth(p5);
    float big = 1.0 - min(min(g5.x, g5.y), 1.0);
    vec3 col = mix(uG, uL, clamp(fine * 0.35 + big * 0.55, 0.0, 1.0));
    float d = length(vW.xz - uC.xz);
    gl_FragColor = vec4(mix(col, uBg, smoothstep(0.08, 0.26, d)), 1.0);
  }`;

export function createTriggerStage({canvas}) {
  const renderer = new THREE.WebGLRenderer({canvas, antialias: false, preserveDrawingBuffer: true, powerPreference: 'high-performance'});
  renderer.toneMapping = THREE.NeutralToneMapping;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.VSMShadowMap;
  renderer.localClippingEnabled = true;
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(COL.bg);
  const camera = new THREE.PerspectiveCamera(26, 16 / 9, 0.002, 4);
  const composer = new EffectComposer(renderer, new THREE.WebGLRenderTarget(4, 4, {type: THREE.HalfFloatType, samples: 8}));
  composer.addPass(new RenderPass(scene, camera));
  const gtao = new GTAOPass(scene, camera, 4, 4);
  gtao.output = GTAOPass.OUTPUT.Default;
  gtao.blendIntensity = 0.85;
  gtao.updateGtaoMaterial({radius: 0.006, distanceExponent: 1.4, thickness: 0.04, scale: 1.0, samples: 16, distanceFallOff: 1.0, screenSpaceRadius: false});
  gtao.updatePdMaterial({lumaPhi: 10, depthPhi: 2, normalPhi: 3, radius: 5, rings: 2, samples: 16});
  class Toggle extends Pass {
    constructor(fn) {
      super();
      this.needsSwap = false;
      this.fn = fn;
    }
    render() { this.fn(); }
  }
  const groundVis = (v) => () => {
    ground.visible = v;
    shade.visible = v;
  };
  composer.addPass(new Toggle(groundVis(false)));
  composer.addPass(gtao);
  composer.addPass(new Toggle(groundVis(true)));
  composer.addPass(new OutputPass());

  {
    const env = new THREE.Scene();
    env.background = new THREE.Color('#e4e0d8');
    const box = (w, h, pos, k) => {
      const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({color: new THREE.Color(1, 0.99, 0.97).multiplyScalar(k), side: THREE.DoubleSide}));
      m.position.copy(pos);
      m.lookAt(0, 0, 0);
      env.add(m);
    };
    box(0.5, 0.5, new V3(0, 0.6, 0.1), 2.6);
    box(0.16, 0.6, new V3(-0.5, 0.15, 0.25), 3.0);
    box(0.16, 0.6, new V3(0.5, 0.15, -0.15), 1.9);
    box(0.8, 0.1, new V3(0, 0.05, 0.6), 1.4);
    const g = new THREE.Mesh(new THREE.CircleGeometry(2, 24), new THREE.MeshBasicMaterial({color: '#cfc8bc', side: THREE.DoubleSide}));
    g.rotation.x = -Math.PI / 2;
    g.position.y = -0.1;
    env.add(g);
    const pm = new THREE.PMREMGenerator(renderer);
    scene.environment = pm.fromScene(env, 0.02).texture;
    scene.environmentIntensity = 1.0;
    pm.dispose();
  }
  const SUN_DIR = new V3(-0.4, 0.85, 0.5).normalize();
  const sun = new THREE.DirectionalLight('#fff8ee', 2.1);
  sun.castShadow = true;
  const EXT = 0.07;
  Object.assign(sun.shadow.camera, {left: -EXT, right: EXT, top: EXT, bottom: -EXT, near: 0.02, far: 0.6});
  sun.shadow.mapSize.set(4096, 4096);
  sun.shadow.radius = 7;
  sun.shadow.blurSamples = 18;
  sun.shadow.bias = -0.00004;
  sun.shadow.normalBias = 0.0004;
  sun.position.copy(SUN_DIR).multiplyScalar(0.25);
  scene.add(sun, sun.target);
  scene.add(new THREE.HemisphereLight('#fffdf8', '#cdc5b7', 0.6));

  const groundMat = new THREE.ShaderMaterial({
    vertexShader: G_VERT,
    fragmentShader: G_FRAG,
    uniforms: {uG: {value: new THREE.Color(COL.ground)}, uL: {value: new THREE.Color(COL.grid)}, uBg: {value: new THREE.Color(COL.bg)}, uC: {value: new V3()}},
    toneMapped: false,
  });
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), groundMat);
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = GROUND_Y;
  scene.add(ground);
  const shade = new THREE.Mesh(
    new THREE.PlaneGeometry(1, 1),
    new THREE.ShadowMaterial({color: COL.shadow, opacity: 0.26, polygonOffset: true, polygonOffsetFactor: -4, polygonOffsetUnits: -8}),
  );
  shade.rotation.x = -Math.PI / 2;
  shade.position.y = GROUND_Y;
  shade.receiveShadow = true;
  scene.add(shade);

  const mod = buildModule();
  scene.add(mod.root);

  const size = {w: 1600, h: 900};
  const resize = (w, h, pr) => {
    size.w = w; size.h = h;
    renderer.setPixelRatio(pr);
    renderer.setSize(w, h, false);
    composer.setPixelRatio(pr);
    composer.setSize(w, h);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  };
  /** st: one solve() plus {xray, section, explode}; cam: {tx,ty,tz,az,el,d,sx,sy} radians/metres */
  const frame = (st, cam) => {
    mod.update(st, st);
    const tx = cam.tx, ty = cam.ty, tz = cam.tz;
    camera.position.set(tx + cam.d * Math.cos(cam.el) * Math.sin(cam.az), ty + cam.d * Math.sin(cam.el), tz + cam.d * Math.cos(cam.el) * Math.cos(cam.az));
    camera.lookAt(tx, ty, tz);
    camera.setViewOffset(size.w, size.h, -(cam.sx ?? 0), -(cam.sy ?? 0), size.w, size.h);
    camera.updateMatrixWorld();
    groundMat.uniforms.uC.value.set(tx, 0, tz);
    sun.target.position.set(0, -0.015, -0.015);
    sun.position.copy(sun.target.position).addScaledVector(SUN_DIR, 0.25);
    sun.target.updateMatrixWorld();
    composer.render();
  };
  const pv = new V3();
  const project = (x, y, z) => {
    pv.set(x, y, z).project(camera);
    if (pv.z > 1) return null;
    return [(pv.x * 0.5 + 0.5) * size.w, (-pv.y * 0.5 + 0.5) * size.h];
  };
  const setQuality = ({samples, ao, shadow}) => {
    if (samples !== undefined)
      for (const t of [composer.renderTarget1, composer.renderTarget2]) {
        t.samples = samples;
        t.dispose();
      }
    if (ao !== undefined) gtao.enabled = ao;
    if (shadow !== undefined) {
      sun.shadow.mapSize.set(shadow, shadow);
      sun.shadow.map?.dispose();
      sun.shadow.map = null;
    }
  };
  return {renderer, scene, camera, composer, gtao, sun, mod, resize, frame, project, size, setQuality};
}
