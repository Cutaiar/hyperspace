// Lay out flexcases.json in Chromium and dump the resulting child rects.
//
//   node hyperspace/dkit/dev/flex_oracle.js > hyperspace/dkit/dev/flexgolden.json
//
// The browser is the spec. Writing a flex implementation from a reading of
// CSS 2.1 §9 and hoping is exactly the kind of thing that is subtly wrong
// forever; this makes conformance a measurement, the same trick the chrome
// diff uses.
const { chromium } = require("playwright")
const fs = require("fs")
const path = require("path")

const SPEC = JSON.parse(
  fs.readFileSync(path.join(__dirname, "flexcases.json"), "utf8"))

;(async () => {
  const b = await chromium.launch({ args: ["--no-sandbox"] })
  const p = await b.newPage({ viewport: { width: 1600, height: 900 } })
  await p.setContent("<!doctype html><meta charset=utf-8><body style='margin:0'>")

  const out = await p.evaluate((spec) => {
    const res = {}
    for (const c of spec.cases) {
      const box = document.createElement("div")
      const [pt, pr, pb, pl] = c.pad
      box.style.cssText = [
        "position:absolute", "left:0", "top:0", "box-sizing:border-box",
        `width:${c.box[0]}px`, `height:${c.box[1]}px`,
        "display:flex", `flex-direction:${c.dir}`, `gap:${c.gap}px`,
        `justify-content:${c.justify}`, `align-items:${c.align}`,
        `padding:${pt}px ${pr}px ${pb}px ${pl}px`,
      ].join(";")
      for (const it of c.items) {
        const [w, h, grow = 0, shrink = 1] = it
        const d = document.createElement("div")
        const main = c.dir === "row" ? w : h
        d.style.cssText = [
          "box-sizing:border-box",
          w === null ? "" : `width:${w}px`,
          h === null ? "" : `height:${h}px`,
          `flex-grow:${grow}`, `flex-shrink:${shrink}`,
          // flex-basis auto would resolve off width/height; pin it so the
          // case means exactly what it says
          main === null ? "flex-basis:auto" : `flex-basis:${main}px`,
        ].filter(Boolean).join(";")
        box.appendChild(d)
      }
      document.body.appendChild(box)
      const br = box.getBoundingClientRect()
      res[c.id] = [...box.children].map((ch) => {
        const r = ch.getBoundingClientRect()
        return [
          +(r.x - br.x).toFixed(3), +(r.y - br.y).toFixed(3),
          +r.width.toFixed(3), +r.height.toFixed(3),
        ]
      })
      box.remove()
    }
    return res
  }, SPEC)

  process.stdout.write(JSON.stringify(out, null, 1) + "\n")
  await b.close()
})()
