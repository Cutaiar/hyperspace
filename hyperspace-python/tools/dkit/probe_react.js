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

let CTX_AT = null   // where the ContextMenu was opened, for its placement
const args = process.argv.slice(2)
const url = args.find((a) => !a.startsWith("--")) || "http://localhost:4173/?probe"
const jsonAt = args.indexOf("--json")
const jsonOut = jsonAt >= 0 ? args[jsonAt + 1] : null

// The properties that describe chrome. Keep this list tight: a full computed
// style is ~340 properties and the signal drowns.
const PROPS = [
  "backgroundColor", "backgroundImage", "opacity",
  "borderTopWidth", "borderTopColor", "borderTopStyle",
  // All four widths, not just the top: a horizontal ButtonGroup collapses
  // its SHARED edge, which is a left/right border, and a list that carries
  // only borderTopWidth reports 1px for every button and cannot see it.
  "borderRightWidth", "borderBottomWidth", "borderLeftWidth",
  "borderLeftColor",
  // All four corners. borderBottomRightRadius was the one missing, which is
  // exactly the corner a button-group's LAST item rounds.
  "borderTopLeftRadius", "borderTopRightRadius", "borderBottomLeftRadius",
  "borderBottomRightRadius",
  "boxShadow", "outlineWidth", "outlineColor",
  "transform", "translate",
  "paddingTop", "paddingRight", "paddingBottom", "paddingLeft",
  "fontSize", "fontWeight", "lineHeight", "color",
  "width", "height", "overflow",
  // a Dialog/Sheet scrim is `bg-black/10 backdrop-blur-sm`, and the
  // blur is the half of it a draw list cannot do at all
  "backdropFilter", "zIndex", "position", "gap",
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

  // --- the ContextMenu, which only exists after a real right-click ---------
  // Radix's ContextMenu has no `defaultOpen`, so until something actually
  // right-clicks the trigger the only thing under `contextmenu.target` is
  // the trigger itself. The panel had never been measured: every number in
  // comp_context_menu.py came from the DropdownMenu's chrome plus a reading
  // of the classes. Open it BEFORE the static walk below, so the content is
  // in the DOM when the blocks are read.
  {
    const t = p.locator("[data-probe-ctx]").first()
    if (await t.count()) {
      // NOT a real right-click: `?probe` also carries an OPEN Combobox, whose
      // portal covers this trigger and intercepts pointer events, so
      // locator.click({button:"right"}) times out after 30s. Radix opens on
      // the `contextmenu` EVENT, so dispatching it on the trigger reaches the
      // component without going through hit-testing.
      //
      // clientX/clientY are passed because Radix places the panel at the
      // pointer: with the default 0,0 the panel would be measurable but its
      // POSITION would be a measurement of nothing. These coordinates are the
      // ones comp_context_menu.place_at_pointer is checked against.
      const box = await t.boundingBox()
      CTX_AT = { x: Math.round(box.x + 20), y: Math.round(box.y + 20) }
      await t.dispatchEvent("contextmenu", {
        button: 2, clientX: CTX_AT.x, clientY: CTX_AT.y,
        bubbles: true, cancelable: true,
      })
      // Radix mounts the panel in a portal and runs its open animation; the
      // same 700ms the initial load waits for, for the same reason.
      await p.waitForTimeout(700)
    }
  }

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
      // svg too: the Select's chevron and the Tooltip's arrow carry no
      // data-slot, and their offset inside the trigger is exactly what the
      // kit has to reproduce
      for (const el of block.querySelectorAll("[data-slot], svg")) parts.push(rd(el, origin))
      res[id] = { origin: { w: +origin.width.toFixed(3), h: +origin.height.toFixed(3) }, parts }
    }
    // Portalled content (Select, Tooltip) lives at the document root, not
    // inside its probe block, so it has to be collected separately. Measured
    // against the viewport: its position relative to its trigger is what
    // matters and the trigger's own rect is already recorded above.
    const vp = { x: 0, y: 0 }
    const portal = []
    for (const el of document.querySelectorAll(
      // `body > [data-slot]` is not redundant with `body > div > [data-slot]`:
      // a Radix Dialog and Sheet put their OVERLAY and CONTENT as direct
      // children of body, with no portal wrapper, so the two-level selector
      // caught their headers and footers and missed the two slots that
      // matter - the scrim and the panel.
      "body > [data-slot], body > [data-radix-popper-content-wrapper] [data-slot], body > div > [data-slot], [data-slot=\"tooltip-content\"] svg, [data-slot=\"select-content\"] [data-slot], [data-slot=\"select-item\"] svg"
    )) {
      if (el.closest("[data-probe]")) continue
      portal.push(rd(el, vp))
    }
    if (portal.length) res["_portal"] = { parts: portal }
    return res
  }, PROPS)

  // Close the ContextMenu now the walk has recorded it. It is a MODAL layer -
  // Radix puts pointer-events:none on the body while it is open - so leaving
  // it up makes every hover below time out, which is the same trap the
  // ?probe&open Select pass is documented for. Measured, then dismissed.
  if (CTX_AT) {
    await p.keyboard.press("Escape")
    await p.waitForTimeout(300)
  }


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
        // a TabsTrigger carries `focus-visible:outline-1 outline-ring` as
        // well as the ring, which no other control in the kit has
        outlineWidth: cs.outlineWidth, outlineColor: cs.outlineColor,
        outlineStyle: cs.outlineStyle,
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

  // --- Checkbox --------------------------------------------------------
  // The recipe has no `hover:` class; measured anyway, because "no class"
  // is a reading of the source and the hover answer is a measurement.
  for (const st of ["off", "on"]) {
    const sel = `[data-probe="checkbox.${st}"] [data-slot="checkbox"]`
    await grab(`checkbox.${st}.rest`, sel)
    await p.hover(sel)
    await p.waitForTimeout(350)
    await grab(`checkbox.${st}.hover`, sel)
    await p.mouse.move(0, 0)
    // keyboard focus: `data-checked:border-primary` and
    // `focus-visible:border-ring` both set the border, so which one wins on
    // a CHECKED box is a cascade question, answered here rather than read
    await p.locator(sel).evaluate((e) => e.focus())
    await p.waitForTimeout(350)
    await grab(`checkbox.${st}.focus`, sel)
    await p.locator(sel).evaluate((e) => e.blur())
    await p.waitForTimeout(350)
  }
  {
    // The hit area. `after:absolute after:-inset-x-3 after:-inset-y-2`
    // stretches the click target 12px left/right and 8px up/down of a 16px
    // box. Real clicks, one per offset, each read back as toggled or not;
    // the state is restored by a second click at the centre when it did.
    const sel = "[data-probe-cbhit]"
    const box = await p.locator(sel).boundingBox()
    const state = () => p.locator(sel).getAttribute("data-state")
    const hit = {}
    const probe = async (dx, dy) => {
      const before = await state()
      await p.mouse.click(box.x + dx, box.y + dy)
      await p.waitForTimeout(30)
      const after = await state()
      if (after !== before) {
        await p.mouse.click(box.x + box.width / 2, box.y + box.height / 2)
        await p.waitForTimeout(30)
      }
      return after !== before
    }
    const cy = box.height / 2, cx = box.width / 2
    hit.box = { w: box.width, h: box.height }
    hit.x = {}
    for (const dx of [-13, -12.5, -12, -11.5, -1, 0.5, 8, 15.5, 16.5, 27.5, 28, 28.5, 29])
      hit.x[dx] = await probe(dx, cy)
    hit.y = {}
    for (const dy of [-9, -8.5, -8, -7.5, 0.5, 8, 15.5, 23.5, 24, 24.5, 25])
      hit.y[dy] = await probe(cx, dy)
    // after a POINTER click the box has focus but must not match
    // :focus-visible - read the ring straight after one
    await p.mouse.click(box.x + cx, box.y + cy)
    await p.waitForTimeout(350)
    await grab("checkbox.pointer_click", sel)
    states["checkbox.pointer_click"].is_focused = await p.locator(sel)
      .evaluate((e) => document.activeElement === e)
    states["checkbox.pointer_click"].state = await state()
    // and the keyboard: Space toggles; Enter does NOT (a WAI-ARIA checkbox
    // is Space-only, and Radix prevents Enter on it)
    const before = await state()
    await p.keyboard.press("Enter")
    await p.waitForTimeout(30)
    hit.enter_toggles = (await state()) !== before
    const b2 = await state()
    await p.keyboard.press("Space")
    await p.waitForTimeout(30)
    hit.space_toggles = (await state()) !== b2
    // the ::after box itself: its insets resolve against the PADDING box,
    // 1px inside the border, so -inset-x-3 is 11px past the border edge,
    // not 12. Both instruments are recorded so they can be checked against
    // each other - a sparse click scan alone first read this as lopsided.
    hit.after = await p.locator(sel).evaluate((e) => {
      const c = getComputedStyle(e, "::after")
      return { w: parseFloat(c.width), h: parseFloat(c.height),
               left: parseFloat(c.left), top: parseFloat(c.top) }
    })
    states["checkbox.hit"] = hit
    await p.mouse.click(box.x + cx, box.y + cy)   // leave it as found
    await p.locator(sel).evaluate((e) => e.blur())
    await p.mouse.move(0, 0)
  }
  {
    // The transition: `transition-colors` on the root (150ms) but
    // `transition-none` on the indicator, and Radix unmounts the indicator
    // when unchecked. So on a check, does the tick appear at once over a
    // fill that is still easing in? Sampled on the uncontrolled box.
    const sel = "[data-probe-cbhit]"
    const samples = []
    // start from UNCHECKED whatever the hit scan left behind - the first
    // version assumed it, and recorded an uncheck under the label "check"
    if ((await p.locator(sel).getAttribute("data-state")) === "checked") {
      await p.locator(sel).evaluate((e) => e.click())
      await p.waitForTimeout(400)
    }
    await p.locator(sel).evaluate((e) => e.click())
    const t0 = Date.now()
    for (let i = 0; i < 8; i++) {
      samples.push(await p.locator(sel).evaluate((e) => ({
        bg: getComputedStyle(e).backgroundColor,
        border: getComputedStyle(e).borderTopColor,
        tick: !!e.querySelector("svg"),
        state: e.getAttribute("data-state"),
      })))
      samples[samples.length - 1].ms = Date.now() - t0
      await p.waitForTimeout(25)
    }
    states["checkbox.transition.check"] = samples
    await p.waitForTimeout(400)
    await p.locator(sel).evaluate((e) => e.click())
    const un = []
    const t1 = Date.now()
    for (let i = 0; i < 3; i++) {
      un.push(await p.locator(sel).evaluate((e) => ({
        bg: getComputedStyle(e).backgroundColor,
        tick: !!e.querySelector("svg"),
      })))
      un[un.length - 1].ms = Date.now() - t1
      await p.waitForTimeout(25)
    }
    states["checkbox.transition.uncheck"] = un
    await p.locator(sel).evaluate((e) => e.blur())
  }

  // The four controls interact.py rings with nothing. Focused with a real
  // keyboard focus, because `:focus-visible` is the thing being measured and
  // a forced class would measure a guess about what the class resolves to.
  //
  // `.focus()` from script counts as keyboard focus for :focus-visible on a
  // button in Chromium, which is what makes this measurable at all; a
  // pointer click would deliberately NOT match, and that difference is the
  // whole model the kit implements.
  for (const [label, sel] of [
    ["tabs.trigger", "[data-probe-tab]"],
    ["sidebar.button", "[data-probe-sidebtn]"],
    ["table.row", "[data-probe-row]"],
  ]) {
    await grab(label + ".rest", sel)
    const el = p.locator(sel).first()
    if (await el.count()) {
      await el.evaluate((e) => e.focus())
      await p.waitForTimeout(350)
      await grab(label + ".focus", sel)
      // what the browser thinks has focus, which answers whether the element
      // is focusable AT ALL - a <tr> is not a control and takes no focus, so
      // giving it a ring would be inventing an affordance
      states[label + ".focus"] = states[label + ".focus"] || {}
      states[label + ".focus"].is_focused = await el.evaluate(
        (e) => document.activeElement === e)
      states[label + ".focus"].tabindex = await el.evaluate(
        (e) => e.getAttribute("tabindex"))
      states[label + ".focus"].tag = await el.evaluate(
        (e) => e.tagName.toLowerCase())
      await el.evaluate((e) => e.blur())
    }
  }

  await grab("select.trigger.rest", '[data-probe="select.closed"] [data-slot="select-trigger"]')
  await p.hover('[data-probe="select.closed"] [data-slot="select-trigger"]')
  await p.waitForTimeout(350)
  await grab("select.trigger.hover", '[data-probe="select.closed"] [data-slot="select-trigger"]')
  await p.mouse.move(0, 0)

  }

  out._states = states
  // Where the contextmenu event was dispatched, so the panel's rect can be
  // read as an OFFSET from the pointer rather than an absolute position.
  if (CTX_AT) out._ctx_at = CTX_AT

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
    // `_states` is not a block: it is a flat name -> style map of the
    // hover/focus/active passes, collected separately above. Printing it
    // through the part loop is how this crashed with "blk.parts is not
    // iterable" - which took the whole dump out, since the write happens
    // first and the print is all anyone sees without --json.
    if (id === "_states" || id === "_ctx_at") continue
    console.log(`\n=== ${id} ===`)
    for (const part of blk.parts) {
      const geo = `${part.w.toFixed(2)}x${part.h.toFixed(2)} @ ${part.x.toFixed(2)},${part.y.toFixed(2)}`
      console.log(`  ${part.slot.padEnd(22)} ${geo}${part.state ? "  [" + part.state + "]" : ""}`)
      const keep = Object.entries(part.style).filter(([k, v]) => !dull(k, v))
      for (const [k, v] of keep) console.log(`      ${k.padEnd(22)} ${v}`)
    }
  }

  // The state passes, which carry no rect of their own beyond w/h.
  if (out._states) {
    console.log(`\n=== _states (hover / focus / active) ===`)
    for (const [name, st] of Object.entries(out._states)) {
      const { w, h, ...style } = st
      console.log(`  ${name.padEnd(26)} ${Number(w).toFixed(2)}x${Number(h).toFixed(2)}`)
      for (const [k, v] of Object.entries(style)) {
        if (!dull(k, v)) console.log(`      ${k.padEnd(22)} ${v}`)
      }
    }
  }
  await b.close()
})()
