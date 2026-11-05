// Screenshot the React oracle at exactly the spec canvas size, DPR 1.
//
//   node tools/dkit/capture_react.js <url> <out-dir>
//
// Shoots the #dkit-canvas element rather than the viewport, so page margins
// and scrollbars cannot shift the origin.
const { chromium } = require("playwright")

const url = process.argv[2] || "http://localhost:4173/?gallery"
const out = process.argv[3] || "/tmp/dkit"

;(async () => {
  const b = await chromium.launch({ args: ["--no-sandbox", "--force-device-scale-factor=1"] })
  const p = await b.newPage({ viewport: { width: 1200, height: 700 }, deviceScaleFactor: 1 })
  const errs = []
  p.on("pageerror", (e) => errs.push(String(e)))
  await p.goto(url, { waitUntil: "networkidle", timeout: 60000 })
  await p.waitForSelector("#dkit-canvas", { timeout: 15000 })
  // Fonts settle after load; a stale fallback face would move text, and in the
  // chrome pass would still change nothing, but wait anyway for the text pass.
  await p.evaluate(() => document.fonts.ready)
  await p.waitForTimeout(400)
  const el = p.locator("#dkit-canvas")
  const box = await el.boundingBox()
  await el.screenshot({ path: `${out}/react.png` })
  console.log(`wrote ${out}/react.png  ${Math.round(box.width)}x${Math.round(box.height)}`)
  if (errs.length) console.log("page errors:\n" + errs.join("\n"))
  await b.close()
})()
