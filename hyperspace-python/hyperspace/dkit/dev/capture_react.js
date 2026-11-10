// Screenshot the React oracle at exactly the spec canvas size, DPR 1.
//
//   node hyperspace/dkit/dev/capture_react.js <url> <out-dir>
//
// Shoots the #dkit-canvas element rather than the viewport, so page margins
// and scrollbars cannot shift the origin.
const { chromium } = require("playwright")
const spec = require("./spec.json")

const url = process.argv[2] || "http://localhost:4173/?gallery"
const out = process.argv[3] || "/tmp/dkit"

;(async () => {
  const b = await chromium.launch({ args: ["--no-sandbox", "--force-device-scale-factor=1"] })
  // The viewport must COMFORTABLY exceed the spec canvas. Anything placed
  // by floating-ui - a menu, a tooltip, a popover - asks the live viewport
  // whether it fits, and flips if it does not. With a 700px viewport and a
  // 1300px canvas the menu cell was off-screen, so Radix placed its panel
  // ABOVE the trigger and the diff compared two different sides.
  //
  // DERIVED from the spec, not a constant. It was 1600 against a 1300px
  // canvas, and adding cells took the canvas past it: the ContextMenu panel
  // was then collision-clamped to the top-left of the page, 1490px from the
  // cell it belongs to. A margin that has to be remembered when the spec
  // grows is a margin that will not be.
  const p = await b.newPage({
    viewport: { width: spec.canvas.w + 400, height: spec.canvas.h + 400 },
    deviceScaleFactor: 1,
  })
  const errs = []
  p.on("pageerror", (e) => errs.push(String(e)))
  await p.goto(url, { waitUntil: "networkidle", timeout: 60000 })
  await p.waitForSelector("#dkit-canvas", { timeout: 15000 })
  // Fonts settle after load; a stale fallback face would move text, and in the
  // chrome pass would still change nothing, but wait anyway for the text pass.
  await p.evaluate(() => document.fonts.ready)
  await p.waitForTimeout(400)
  // A ContextMenu cell cannot be opened declaratively - Radix drives it from
  // a real contextmenu gesture - so the cell renders a 0x0 trigger at its own
  // top-left and it is opened here. dispatchEvent rather than a right-click
  // for the same reason the probe uses it: the gallery stacks portalled
  // panels (the tooltip, the menu) that can sit over the anchor and intercept
  // a real pointer event. The panel lands where RADIX puts it; the spec rect
  // is the measured result, so nothing about the offset is duplicated here.
  for (const t of await p.locator("[data-ctx-anchor]").all()) {
    const box = await t.boundingBox()
    // A REAL right-click, at the trigger's top-left. dispatchEvent was tried
    // first and does not work here: Playwright does not put clientX/clientY
    // on the synthesised event, so Radix read the pointer as (0, 0) and put
    // the panel in the corner of the page. The cell pins its trigger 2px
    // left of itself to absorb Radix's offset, so this corner IS the anchor.
    await p.mouse.click(box.x, box.y, { button: "right" })
  }
  if (await p.locator("[data-ctx-anchor]").count()) {
    // past the open animation, which `animation: none` on the content does
    // not cover: Radix also sets a transform on the popper wrapper
    await p.waitForTimeout(500)
  }

  const el = p.locator("#dkit-canvas")
  const box = await el.boundingBox()
  await el.screenshot({ path: `${out}/react.png` })
  console.log(`wrote ${out}/react.png  ${Math.round(box.width)}x${Math.round(box.height)}`)
  if (errs.length) console.log("page errors:\n" + errs.join("\n"))
  await b.close()
})()
