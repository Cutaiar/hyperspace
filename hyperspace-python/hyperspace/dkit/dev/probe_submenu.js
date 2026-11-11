// Measure a shadcn ContextMenu SUBMENU in Chromium, and print what it is.
//
//   node hyperspace/dkit/dev/probe_submenu.js [url] [--json out.json] [--dark]
//
// `probe_react.js` walks the DOM once, so it only ever sees the first level
// of a menu: a Radix SubContent is not mounted until its SubTrigger is
// HOVERED (or opened with a key), which is a gesture and not a selector.
// Every number menu.py needs for a submenu — the panel's own chrome, where
// it lands beside its parent, how long the hover takes to open it, and which
// keys open and close it — therefore comes from here.
//
// The block it reads is `contextmenu.sub` on ?probe (src/Probe.tsx).
const { chromium } = require("playwright")
const fs = require("fs")

const args = process.argv.slice(2)
const dark = args.includes("--dark")
const jsonAt = args.indexOf("--json")
const jsonOut = jsonAt >= 0 ? args[jsonAt + 1] : null
// skip --json's VALUE as well as the flags: it is a path, and a path is the
// one thing that looks like a positional url and is not one
const url = args.find((a, i) => !a.startsWith("--") && i !== jsonAt + 1)
  || "http://localhost:4173/?probe"

const PROPS = [
  "backgroundColor", "opacity", "minWidth", "width", "height",
  "borderTopWidth", "borderTopColor", "borderTopStyle", "borderLeftWidth",
  "borderTopLeftRadius", "borderBottomRightRadius",
  "boxShadow", "outlineWidth", "overflow", "zIndex",
  "paddingTop", "paddingRight", "paddingBottom", "paddingLeft",
  "fontSize", "fontWeight", "lineHeight", "color", "gap", "transform",
]

const rect = (el, style) => {
  const r = el.getBoundingClientRect()
  const o = { x: +r.x.toFixed(3), y: +r.y.toFixed(3), w: +r.width.toFixed(3), h: +r.height.toFixed(3) }
  const st = el.getAttribute("data-state")
  if (st) o.state = st
  if (style) {
    const cs = getComputedStyle(el)
    o.style = {}
    for (const k of style) o.style[k] = cs[k]
  }
  return o
}

;(async () => {
  const b = await chromium.launch({ args: ["--no-sandbox", "--force-device-scale-factor=1"] })
  const p = await b.newPage({ viewport: { width: 1200, height: 900 }, deviceScaleFactor: 1 })
  const errs = []
  p.on("pageerror", (e) => errs.push(String(e)))
  await p.goto(url + (dark ? "&dark" : ""), { waitUntil: "networkidle", timeout: 60000 })
  await p.waitForSelector("#dkit-probe", { timeout: 15000 })
  await p.evaluate(() => document.fonts.ready)
  await p.waitForTimeout(700)
  await p.addScriptTag({ content: `window.__rect = ${rect.toString()}` })

  const out = { url, dark }

  // --- open the context menu, exactly as probe_react.js does ---------------
  // A dispatched `contextmenu`, not a real right-click: ?probe also carries
  // an open Combobox whose portal intercepts pointer events over this part
  // of the page.
  const t = p.locator("[data-probe-ctxsub]").first()
  const box = await t.boundingBox()
  const at = { x: Math.round(box.x + 20), y: Math.round(box.y + 20) }
  out.pointer = at
  await t.dispatchEvent("contextmenu", {
    button: 2, clientX: at.x, clientY: at.y, bubbles: true, cancelable: true,
  })
  await p.waitForTimeout(700)

  // --- the parent panel and the SubTrigger row, at rest -------------------
  out.rest = await p.evaluate((PROPS) => {
    const panel = document.querySelector('[data-slot="context-menu-content"]')
    const trig = document.querySelector('[data-probe-subtrigger]')
    const rows = [...document.querySelectorAll('[data-slot="context-menu-content"] > *')]
      .map((el) => ({ slot: el.getAttribute("data-slot"), ...window.__rect(el, null) }))
    return {
      panel: panel && window.__rect(panel, PROPS),
      trigger: trig && window.__rect(trig, PROPS),
      chevron: trig && trig.querySelector("svg") && window.__rect(trig.querySelector("svg"), ["width", "height"]),
      rows,
      sub_mounted: !!document.querySelector('[data-probe-subcontent]'),
    }
  }, PROPS)

  // --- how long the hover takes to open it --------------------------------
  // Radix's SubTrigger opens on pointer-move with a timer. The delay is the
  // thing a reading of the classes cannot give at all.
  {
    const tb = await p.locator("[data-probe-subtrigger]").boundingBox()
    const cx = Math.round(tb.x + tb.width / 2), cy = Math.round(tb.y + tb.height / 2)
    await p.mouse.move(cx - 40, cy + 40)
    await p.waitForTimeout(200)
    const t0 = Date.now()
    await p.mouse.move(cx, cy)
    let opened = null
    for (let i = 0; i < 120; i++) {
      const up = await p.evaluate(() => !!document.querySelector('[data-probe-subcontent]'))
      if (up) { opened = Date.now() - t0; break }
      await p.waitForTimeout(10)
    }
    out.hover_open_ms = opened
    await p.waitForTimeout(600)      // past the 100ms zoom-in
  }

  // --- the SubContent panel, open ----------------------------------------
  out.open = await p.evaluate((PROPS) => {
    const panel = document.querySelector('[data-slot="context-menu-content"]')
    const sub = document.querySelector('[data-probe-subcontent]')
    const trig = document.querySelector('[data-probe-subtrigger]')
    const rows = sub ? [...sub.children].map((el) => ({
      slot: el.getAttribute("data-slot"), ...window.__rect(el, ["fontSize", "lineHeight", "color", "backgroundColor"]),
    })) : []
    const pr = panel.getBoundingClientRect(), sr = sub.getBoundingClientRect()
    const tr = trig.getBoundingClientRect()
    return {
      panel: window.__rect(panel, ["minWidth"]),
      sub: window.__rect(sub, PROPS),
      trigger: window.__rect(trig, ["backgroundColor", "color"]),
      rows,
      place: {
        dx_from_panel_right: +(sr.x - pr.right).toFixed(3),
        dx_from_panel_left: +(sr.x - pr.x).toFixed(3),
        dy_from_trigger_top: +(sr.y - tr.y).toFixed(3),
        dy_from_panel_top: +(sr.y - pr.y).toFixed(3),
      },
    }
  }, PROPS)

  // --- the keyboard: ArrowRight opens, ArrowLeft closes -------------------
  // The highlight has to be ON the SubTrigger first, so this walks ArrowDown
  // until it lands there rather than assuming a row count. The pointer is
  // parked off the panel: a pointer resting on a row owns the highlight and
  // would decide the answer instead of the keys.
  {
    await p.keyboard.press("Escape")
    await p.waitForTimeout(300)
    await p.mouse.move(1100, 850)
    await t.dispatchEvent("contextmenu", {
      button: 2, clientX: at.x, clientY: at.y, bubbles: true, cancelable: true,
    })
    await p.waitForTimeout(500)
    const seen = async () => p.evaluate(() => {
      const sub = document.querySelector('[data-probe-subcontent]')
      const hi = [...document.querySelectorAll("[data-highlighted]")]
        .map((e) => (e.textContent || "").trim())
      return { sub: !!sub, highlighted: hi }
    })
    const keys = { on_open: await seen() }
    for (let i = 0; i < 6; i++) {
      const st = await seen()
      if (st.highlighted.join("|").includes("Insert")) break
      await p.keyboard.press("ArrowDown")
      await p.waitForTimeout(200)
    }
    keys.on_subtrigger = await seen()
    await p.keyboard.press("ArrowRight")
    await p.waitForTimeout(300)
    keys.ArrowRight = await seen()
    await p.keyboard.press("ArrowDown")
    await p.waitForTimeout(200)
    keys.then_ArrowDown = await seen()
    await p.keyboard.press("ArrowLeft")
    await p.waitForTimeout(300)
    keys.ArrowLeft = await seen()
    // Enter and Space on the trigger: Radix lists them beside ArrowRight in
    // SUB_OPEN_KEYS, which is a reading of the source until it is driven.
    await p.keyboard.press("Enter")
    await p.waitForTimeout(300)
    keys.Enter_on_subtrigger = {
      ...(await seen()),
      panel: await p.evaluate(() => !!document.querySelector('[data-slot="context-menu-content"]')),
    }
    await p.keyboard.press("ArrowLeft")
    await p.waitForTimeout(250)
    await p.keyboard.press(" ")
    await p.waitForTimeout(300)
    keys.Space_on_subtrigger = {
      ...(await seen()),
      panel: await p.evaluate(() => !!document.querySelector('[data-slot="context-menu-content"]')),
    }
    await p.keyboard.press("ArrowLeft")
    await p.waitForTimeout(250)
    // Escape from inside a submenu: does it close the sub only, or the lot?
    await p.keyboard.press("ArrowRight")
    await p.waitForTimeout(300)
    await p.keyboard.press("Escape")
    await p.waitForTimeout(300)
    keys.Escape_in_sub = {
      ...(await seen()),
      panel: await p.evaluate(() => !!document.querySelector('[data-slot="context-menu-content"]')),
    }
    out.keys = keys
  }

  // --- does hovering another parent row close the submenu? ----------------
  {
    await p.keyboard.press("Escape")
    await p.waitForTimeout(300)
    await t.dispatchEvent("contextmenu", {
      button: 2, clientX: at.x, clientY: at.y, bubbles: true, cancelable: true,
    })
    await p.waitForTimeout(500)
    const tb = await p.locator("[data-probe-subtrigger]").boundingBox()
    await p.mouse.move(Math.round(tb.x + tb.width / 2), Math.round(tb.y + tb.height / 2))
    await p.waitForTimeout(500)
    const opened = await p.evaluate(() => !!document.querySelector('[data-probe-subcontent]'))
    // the row above the trigger, moving LEFTWARD inside the parent panel
    await p.mouse.move(Math.round(tb.x + 20), Math.round(tb.y - 14))
    const steps = []
    for (const ms of [0, 100, 200, 400, 800]) {
      await p.waitForTimeout(ms)
      steps.push({ after_ms: ms, sub: await p.evaluate(() => !!document.querySelector('[data-probe-subcontent]')) })
    }
    out.leave = { opened, steps }
  }

  // --- the right edge: where does a submenu go when it does not fit? -----
  // The graph canvas opens menus wherever the pointer is, including hard
  // against the window's right edge, so the flip is not academic. The
  // VIEWPORT is narrowed rather than the click moved: the probe block is 420
  // wide and a 1200px page can always fit both panels, so a click inside it
  // never reaches an edge.
  {
    await p.keyboard.press("Escape")
    await p.waitForTimeout(300)
    await p.setViewportSize({ width: 250, height: 700 })
    await p.waitForTimeout(300)
    await p.locator("[data-probe-ctxsub]").scrollIntoViewIfNeeded()
    await p.waitForTimeout(300)
    const nb = await p.locator("[data-probe-ctxsub]").boundingBox()
    // as far right as the trigger reaches, so the parent itself has to flip
    const ed = { x: Math.round(nb.x + nb.width - 6), y: Math.round(nb.y + 20) }
    await p.locator("[data-probe-ctxsub]").dispatchEvent("contextmenu", {
      button: 2, clientX: ed.x, clientY: ed.y, bubbles: true, cancelable: true,
    })
    await p.waitForTimeout(600)
    const tb2 = await p.locator("[data-probe-subtrigger]").boundingBox()
    await p.mouse.move(Math.round(tb2.x + tb2.width / 2), Math.round(tb2.y + tb2.height / 2))
    await p.waitForTimeout(700)
    out.edge = await p.evaluate((click) => {
      const panel = document.querySelector('[data-slot="context-menu-content"]')
      const sub = document.querySelector('[data-probe-subcontent]')
      const trig = document.querySelector('[data-probe-subtrigger]')
      const vw = window.innerWidth
      const r = (e) => e && { x: +e.getBoundingClientRect().x.toFixed(3),
                              right: +e.getBoundingClientRect().right.toFixed(3),
                              w: +e.getBoundingClientRect().width.toFixed(3),
                              y: +e.getBoundingClientRect().y.toFixed(3) }
      const pr = r(panel), sr = r(sub), tr = r(trig)
      return {
        viewport_w: vw, click, panel: pr, trigger: tr, sub: sr,
        parent_flipped: pr && pr.x < click.x,
        sub_flipped: sr && tr && sr.x < tr.x,
        sub_right_minus_trigger_left: sr && tr ? +(sr.right - tr.x).toFixed(3) : null,
      }
    }, ed)
  }

  // --- the WIDTH law: a SubTrigger and a sub row at max-content ----------
  // `min-w-36` floors the block above at 144, so nothing there says how wide
  // a row with a chevron wants to be. This block's labels are long enough
  // that the content decides, which pins `measure`'s reservation.
  {
    await p.keyboard.press("Escape")
    await p.waitForTimeout(300)
    await p.setViewportSize({ width: 1200, height: 900 })
    await p.waitForTimeout(300)
    const w = p.locator("[data-probe-ctxwide]").first()
    const wb = await w.boundingBox()
    await w.dispatchEvent("contextmenu", {
      button: 2, clientX: Math.round(wb.x + 20), clientY: Math.round(wb.y + 20),
      bubbles: true, cancelable: true,
    })
    await p.waitForTimeout(600)
    const wt = await p.locator("[data-probe-widetrigger]").boundingBox()
    await p.mouse.move(Math.round(wt.x + wt.width / 2), Math.round(wt.y + wt.height / 2))
    await p.waitForTimeout(700)
    out.width_law = await p.evaluate(() => {
      const panel = document.querySelector('[data-probe-ctxwide]')
      const trig = document.querySelector('[data-probe-widetrigger]')
      const sub = document.querySelector('[data-probe-widecontent]')
      const row = sub && sub.querySelector('[data-slot="context-menu-item"]')
      const span = (el, text) => {
        // the label's own ink extent, so the reservation either side of it
        // can be read off rather than inferred
        const r = document.createRange()
        r.selectNodeContents(el)
        const b = r.getBoundingClientRect()
        return { x: +b.x.toFixed(4), w: +b.width.toFixed(4), text }
      }
      const tp = trig.closest('[data-slot="context-menu-content"]')
      return {
        parent_panel: { x: +tp.getBoundingClientRect().x.toFixed(3), w: +tp.getBoundingClientRect().width.toFixed(4) },
        trigger: { x: +trig.getBoundingClientRect().x.toFixed(3), w: +trig.getBoundingClientRect().width.toFixed(4) },
        trigger_text: span(trig, trig.textContent.trim()),
        chevron: (() => { const c = trig.querySelector("svg").getBoundingClientRect()
                          return { x: +c.x.toFixed(3), w: +c.width.toFixed(3) } })(),
        sub_panel: sub && { x: +sub.getBoundingClientRect().x.toFixed(3), w: +sub.getBoundingClientRect().width.toFixed(4) },
        sub_row: row && { x: +row.getBoundingClientRect().x.toFixed(3), w: +row.getBoundingClientRect().width.toFixed(4) },
        sub_row_text: row && span(row, row.textContent.trim()),
        // is the chevron RESERVED or does it sit over the label? scrollWidth
        // past clientWidth says the row's content overflows its box, which
        // is the only way the two measurements above can both be right.
        overflow: {
          trigger_h: trig.getBoundingClientRect().height,
          trigger_client_w: trig.clientWidth,
          trigger_scroll_w: trig.scrollWidth,
          trigger_white_space: getComputedStyle(trig).whiteSpace,
          text_nodes: [...trig.childNodes].map((n) => n.nodeType === 3 ? "#text" : n.tagName),
          svg_style: (() => { const cs = getComputedStyle(trig.querySelector("svg"))
                              return { marginLeft: cs.marginLeft, flexShrink: cs.flexShrink,
                                       position: cs.position, width: cs.width } })(),
        },
      }
    })
  }

  out.errors = errs
  await b.close()
  const text = JSON.stringify(out, null, 2)
  if (jsonOut) fs.writeFileSync(jsonOut, text)
  console.log(text)
})()
