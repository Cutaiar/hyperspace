// Records demo.mp4: the page on a stepped clock, a screenshot a frame,
// piped to ffmpeg, the controls clicked between segments. Serve this
// folder first (`npx http-server -p 8124 -s .`), then:
//
//   node tools/record.mjs http://127.0.0.1:8124/index.html demo.mp4
//
// PLAYWRIGHT: the playwright package's index.mjs (default: the package
// `playwright`). CHROMIUM: a browser to launch instead of Playwright's own.
// CDN_DIR: a folder holding three@0.160.0's files (build/…, examples/jsm/…)
// to serve in place of jsDelivr, for a machine whose browser cannot reach
// it; unset, the page loads them as it does anywhere.
import { spawn } from 'node:child_process';
import fs from 'node:fs';
const { chromium } = await import(process.env.PLAYWRIGHT || 'playwright');
const [url, out] = process.argv.slice(2);
const CDN = process.env.CDN_DIR, FPS = 30;
// software GL where there is no GPU: WebGL in a headless browser
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM || undefined,
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
if (CDN) {
  await page.route('https://cdn.jsdelivr.net/**', r => r.fulfill({ status: 200, contentType: 'text/javascript',
    headers: { 'access-control-allow-origin': '*' },
    body: fs.readFileSync(CDN + '/' + r.request().url().split('three@0.160.0/')[1]) }));
  await page.route(/fonts\.(googleapis|gstatic)\.com/, r => r.abort());
}
// a virtual clock: the page's frames advance only when this script steps them
await page.addInitScript(() => {
  let vt = 0; const q = [];
  performance.now = () => vt;
  window.requestAnimationFrame = (cb) => { q.push(cb); return q.length; };
  window.__step = (ms) => { vt += ms; q.splice(0).forEach(cb => cb(vt)); };
});
page.on('pageerror', e => console.log('pageerror', e.message));
await page.goto(url, { waitUntil: 'networkidle' });
await page.evaluate(() => { for (let i = 0; i < 10; i++) __step(1000 / 30); });
const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
  '-c:v', 'libx264', '-preset', 'slow', '-crf', '26', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out]);
let n = 0;
async function hold(sec) {
  for (let f = 0; f < Math.round(sec * FPS); f++) {
    await page.evaluate(() => __step(1000 / 30));
    const png = await page.screenshot({ type: 'png' });
    if (!ff.stdin.write(png)) await new Promise(r => ff.stdin.once('drain', r));
    n++;
  }
}
const click = (sel) => page.click(sel);
await hold(4);
await click('#form-flat'); await hold(3.5);
await click('#form-3d'); await hold(2.5);
for (const [look, sec] of [['chrome', 3], ['glass', 3], ['pearl', 2.5], ['toon', 2.5], ['halftone', 2.5], ['plasma', 2.5], ['hyper', 2.5]]) {
  await click(`#look [data-v="${look}"]`); await hold(sec);
  console.log(look, n);
}
await click('#look [data-v="clay"]'); await click('#tex [data-v="stripes"]'); await hold(2);
await click('#uvmode [data-v="1"]'); await hold(2.5);
await click('#tex [data-v="none"]'); await click('#uvmode [data-v="0"]');
await click('#source [data-v="wordmark"]'); await click('#look [data-v="chrome"]'); await click('#spin [data-v="turn"]'); await hold(4.5);
ff.stdin.end();
await new Promise(r => ff.on('close', r));
console.log('frames', n);
await browser.close();
