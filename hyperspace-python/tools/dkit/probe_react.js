// Measure the real shadcn components in Chromium, and print what they are.
//
//   node tools/dkit/probe_react.js [url] [--json out.json]
//
// This is the oracle step for every component in the kit. It walks each
// [data-probe] block on the ?probe route and, for the block and every
// [data-slot] inside it (including the portalled ones a Select or Tooltip
// renders at the document root), prints the rect relative to the block plus
// the computed styles that describe chrome: colours, radii, borders, shadows,
// transforms, padding, font.
//
// Why bother when the Tailwind classes are right there: because reading them
// is how you get it wrong. `data-[size=default]:h-[18.4px]` is not a number
// anyone guesses, `bg-white` on the slider thumb is a literal rather than a
// token (so it does NOT swap in dark), and Radix's thumb placement insets by
// the thumb's own width in a way no class states. Every one of those came
// out of this dump.
const { chromium } = require("playwright")
const fs = require("fs")

const args = process.argv.slice(2)
const url = args.find((a) => !a.startsWith("--")) || "http://localhost:4173/?probe"
const jsonAt = args.indexOf("--json")
const jsonOut = jsonAt >= 0 ? args[jsonAt + 1] : null

// The properties that describe chrome. Keep this list tight: a full computed
// style is ~340 properties and the signal drowns.
const PROPS = [
  "backgroundColor", "backgroundImage", "opacity",
  "borderTopWidth", "borderTopColor", "borderTopStyle",
  "borderTopLeftRadius", "borderTopRightRadius", "borderBottomLeftRadius",
  "boxShadow", "outlineWidth", "outlineColor",
  "transform", "translate",
  "paddingTop", "paddingRight", "paddingBottom", "paddingLeft",
  "fontSize", "fontWeight", "lineHeight", "color",
  "width", "height", "overflow",
]

;(async () => {
  const b = await chromium.launch({
    args: ["--no-sandbox", "--force-device-scale-factor=1"],
  })
  const p = await b.newPage({
    viewport: { width: 1200, height: 900 },
    deviceScaleFactor: 1,
  })
  const errs = []
  p.on("pageerror", (e) => errs.push(String(e)))
  await p.goto(url, { waitUntil: "networkidle", timeout: 60000 })
  await p.waitForSelector("#dkit-probe", { timeout: 15000 })
  await p.evaluate(() => document.fonts.ready)
  // Radix mounts portals and runs its open animation after paint; a tooltip
  // or select measured too early reports its pre-animation transform.
  await p.waitForTimeout(700)

  const out = await p.evaluate((PROPS) => {
    const rd = (el, origin) => {
      const r = el.getBoundingClientRect()
      const cs = getComputedStyle(el)
      const o = {
        slot: el.getAttribute("data-slot") || el.tagName.toLowerCase(),
        x: +(r.x - origin.x).toFixed(3),
        y: +(r.y - origin.y).toFixed(3),
        w: +r.width.toFixed(3),
        h: +r.height.toFixed(3),
        style: {},
      }
      for (const k of PROPS) o.style[k] = cs[k]
      const st = el.getAttribute("data-state")
      if (st) o.state = st
      return o
    }
    const res = {}
    for (const block of document.querySelectorAll("[data-probe]")) {
      const id = block.getAttribute("data-probe")
      const origin = block.getBoundingClientRect()
      const parts = [rd(block, origin)]
      for (const el of block.querySelectorAll("[data-slot]")) parts.push(rd(el, origin))
      res[id] = { origin: { w: +origin.width.toFixed(3), h: +origin.height.toFixed(3) }, parts }
    }
    // Portalled content (Select, Tooltip) lives at the document root, not
    // inside its probe block, so it has to be collected separately. Measured
    // against the viewport: its position relative to its trigger is what
    // matters and the trigger's own rect is already recorded above.
    const vp = { x: 0, y: 0 }
    const portal = []
    for (const el of document.querySelectorAll(
      "body > [data-radix-popper-content-wrapper] [data-slot], body > div > [data-slot]"
    )) {
      if (el.closest("[data-probe]")) continue
      portal.push(rd(el, vp))
    }
    if (portal.length) res["_portal"] = { parts: portal }
    return res
  }, PROPS)

  // --- interactive states -------------------------------------------------
  // The rest states above come out of one static dump, but the states the
  // kit has to ANIMATE are reachable only by actually hovering and focusing:
  // `hover:ring-3` and `focus-visible:ring-3` are box-shadows that do not
  // exist in the computed style until the pseudo-class matches. Forcing them
  // with a class would measure a guess about what the class resolves to,
  // which is the mistake this whole harness exists to avoid.
  const states = {}
  const grab = async (label, sel) => {
    const el = p.locator(sel).first()
    if (!(await el.count())) return
    states[label] = await el.evaluate((e) => {
      const r = e.getBoundingClientRect()
      const cs = getComputedStyle(e)
      return {
        w: +r.width.toFixed(3), h: +r.height.toFixed(3),
        backgroundColor: cs.backgroundColor,
        borderTopColor: cs.borderTopColor, borderTopWidth: cs.borderTopWidth,
        boxShadow: cs.boxShadow, transform: cs.transform,
        borderTopLeftRadius: cs.borderTopLeftRadius,
      }
    })
  }

  // The chevron the trigger draws, and the arrow a tooltip draws: neither
  // carries a data-slot, so they are addressed structurally. These come
  // first, while the Select is still open — it is a modal layer, so once it
  // closes its items are gone, and while it is open it swallows every hover.
  await grab("select.chevron", '[data-probe="select.closed"] [data-slot="select-trigger"] svg')
  await grab("tooltip.arrow", '[data-slot="tooltip-content"] svg')
  await grab("select.item", '[data-slot="select-item"]')
  await grab("select.content", '[data-slot="select-content"]')

  // With ?probe&open the page carries a modal Select, which puts
  // pointer-events:none on the body — no hover is reachable, so that pass is
  // for the open-popover geometry only.
  if (!url.includes("open")) {
  await grab("slider.thumb.rest", '[data-probe="slider.w240.v50"] [data-slot="slider-thumb"]')
  await p.hover('[data-probe="slider.w240.v50"] [data-slot="slider-thumb"]')
  await p.waitForTimeout(350)        // past the transition, not inside it
  await grab("slider.thumb.hover", '[data-probe="slider.w240.v50"] [data-slot="slider-thumb"]')
  await p.mouse.down()
  await p.waitForTimeout(350)
  await grab("slider.thumb.active", '[data-probe="slider.w240.v50"] [data-slot="slider-thumb"]')
  await p.mouse.up()
  await p.mouse.move(0, 0)

  await grab("input.rest", '[data-probe="input.value"] input')
  await p.locator('[data-probe="input.value"] input').focus()
  await p.waitForTimeout(350)
  await grab("input.focus", '[data-probe="input.value"] input')
  await p.locator('[data-probe="input.value"] input').blur()

  await grab("switch.track.off", '[data-probe="switch.default.off"] [data-slot="switch"]')
  await p.hover('[data-probe="switch.default.off"] [data-slot="switch"]')
  await p.waitForTimeout(350)
  await grab("switch.track.off.hover", '[data-probe="switch.default.off"] [data-slot="switch"]')
  await p.mouse.move(0, 0)

  await grab("select.trigger.rest", '[data-probe="select.closed"] [data-slot="select-trigger"]')
  await p.hover('[data-probe="select.closed"] [data-slot="select-trigger"]')
  await p.waitForTimeout(350)
  await grab("select.trigger.hover", '[data-probe="select.closed"] [data-slot="select-trigger"]')
  await p.mouse.move(0, 0)

  }

  out._states = states

  if (errs.length) console.log("PAGE ERRORS:\n" + errs.join("\n") + "\n")
  console.log("\n=== interactive states ===")
  for (const [k, v] of Object.entries(states)) {
    console.log(`  ${k}`)
    for (const [kk, vv] of Object.entries(v)) {
      if (vv === "none" || vv === "0px" || vv === "rgba(0, 0, 0, 0)") continue
      console.log(`      ${kk.padEnd(22)} ${vv}`)
    }
  }

  if (jsonOut) {
    fs.writeFileSync(jsonOut, JSON.stringify(out, null, 2))
    console.log(`wrote ${jsonOut}`)
  }

  // Printed compactly: one line per part, with only the styles that are not
  // inert defaults, so a component's chrome fits on a screen.
  const dull = (k, v) =>
    v === "none" || v === "0px" || v === "auto" || v === "normal" ||
    v === "rgba(0, 0, 0, 0)" || v === "visible" || v === "1" ||
    (k === "transform" && v === "none")
  for (const [id, blk] of Object.entries(out)) {
    console.log(`\n=== ${id} ===`)
    for (const part of blk.parts) {
      const geo = `${part.w.toFixed(2)}x${part.h.toFixed(2)} @ ${part.x.toFixed(2)},${part.y.toFixed(2)}`
      console.log(`  ${part.slot.padEnd(22)} ${geo}${part.state ? "  [" + part.state + "]" : ""}`)
      const keep = Object.entries(part.style).filter(([k, v]) => !dull(k, v))
      for (const [k, v] of keep) console.log(`      ${k.padEnd(22)} ${v}`)
    }
  }
  await b.close()
})()
