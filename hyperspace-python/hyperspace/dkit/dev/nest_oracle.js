// Lay nestcases.json out in Chromium and dump every node's rect.
//
//   node hyperspace/dkit/dev/nest_oracle.js > hyperspace/dkit/dev/nestgolden.json
//
// The browser is the spec, the same way flex_oracle.js makes single-line
// flex a measurement rather than a reading of CSS 2.1 §9. Nesting is where
// a hand-written implementation drifts: `height: auto` on a column is the
// sum of its children, on a row it is the tallest of them, and a padded
// parent changes what "auto" resolves to for everything inside it.
const { chromium } = require("playwright")
const fs = require("fs")
const path = require("path")

const SPEC = JSON.parse(
  fs.readFileSync(path.join(__dirname, "nestcases.json"), "utf8"))

;(async () => {
  const b = await chromium.launch({ args: ["--no-sandbox"] })
  const p = await b.newPage({ viewport: { width: 1600, height: 1200 } })
  await p.setContent("<!doctype html><meta charset=utf-8><body style='margin:0'>")

  const out = await p.evaluate((spec) => {
    const build = (n, isRoot, at) => {
      const d = document.createElement("div")
      const [pt, pr, pb, pl] = n.pad || [0, 0, 0, 0]
      const dir = n.dir || "column"
      const css = [
        "box-sizing:border-box", "display:flex",
        `flex-direction:${dir}`, `gap:${n.gap || 0}px`,
        `justify-content:${n.justify || "flex-start"}`,
        `align-items:${n.align || "stretch"}`,
        `padding:${pt}px ${pr}px ${pb}px ${pl}px`,
      ]
      if (isRoot) {
        css.push("position:absolute", `left:${at[0]}px`, `top:${at[1]}px`)
        css.push(at[2] === null ? "width:max-content" : `width:${at[2]}px`)
        css.push(at[3] === null ? "height:auto" : `height:${at[3]}px`)
      } else {
        // a child's main-axis size is its basis; auto means content
        const main = dir === "row" ? n.w : n.h
        if (n.w != null) css.push(`width:${n.w}px`)
        if (n.h != null) css.push(`height:${n.h}px`)
        css.push(`flex-grow:${n.grow || 0}`)
        css.push(`flex-shrink:${n.shrink == null ? 1 : n.shrink}`)
        css.push("flex-basis:auto")
      }
      d.style.cssText = css.filter(Boolean).join(";")
      for (const k of (n.kids || [])) d.appendChild(build(k, false, null))
      return d
    }

    const walk = (el, origin, path, res) => {
      const r = el.getBoundingClientRect()
      res[path] = [
        +(r.x - origin.x).toFixed(3), +(r.y - origin.y).toFixed(3),
        +r.width.toFixed(3), +r.height.toFixed(3),
      ]
      ;[...el.children].forEach((c, i) => walk(c, origin, `${path}.${i}`, res))
    }

    const res = {}
    for (const c of spec.cases) {
      const root = build(c.root, true, c.at)
      document.body.appendChild(root)
      const origin = root.getBoundingClientRect()
      const got = {}
      walk(root, origin, "", got)
      res[c.id] = got
      root.remove()
    }
    return res
  }, SPEC)

  process.stdout.write(JSON.stringify(out, null, 1) + "\n")
  await b.close()
})()
