// Dump Lucide icon geometry to JSON for build_icons.py.
//
//   cd prototypes/dashboard
//   node ../../hyperspace-python/tools/dkit/dump_icons.js > /tmp/lucide.json
//
// lucide-react ships each icon as a structured node list ([tag, attrs]), which
// is better than parsing SVG files: no markup, and the same geometry the React
// dashboard renders. Lucide is ISC licensed.
const fs = require("fs")
const path = require("path")

const WANT = [
  // sidebar and header
  "gauge", "shapes", "layers", "activity", "waves", "music", "box", "boxes",
  // no "github": Lucide dropped brand icons, and the header button is text
  "sparkles", "settings", "life-buoy",
  // stats
  "trending-up", "trending-down",
  // menus and the node editor
  "ellipsis-vertical", "ellipsis", "chevron-down", "chevron-right",
  "chevron-left", "chevron-up", "plus", "minus", "x", "check", "search",
  "trash-2", "copy", "link", "unlink", "eye", "eye-off", "lock", "unlock",
  "play", "pause", "grip-vertical", "pencil", "circle", "info",
  // Hyperspace's side pane (hyperspace/ui_switcher.py): its seven views and
  // its patch strip
  "mouse-pointer-2", "list-music", "users", "route", "cpu", "audio-lines",
  "save", "save-all", "rotate-ccw", "folder-open",
]

const dir = path.join(__dirname, "../../../prototypes/dashboard/node_modules/lucide-react/dist/esm/icons")
const out = {}
const missing = []

for (const name of WANT) {
  const f = path.join(dir, `${name}.mjs`)
  if (!fs.existsSync(f)) { missing.push(name); continue }
  let src = fs.readFileSync(f, "utf8")
  // some names are aliases that just re-export another module
  for (let hop = 0; hop < 4; hop++) {
    const alias = src.match(/export \{ default \} from '\.\/([^']+)'/)
    if (!alias) break
    const g = path.join(dir, alias[1])
    if (!fs.existsSync(g)) break
    src = fs.readFileSync(g, "utf8")
  }
  // the module is ESM with a license header; pull the literal out rather than
  // importing, so this runs under plain CommonJS node
  const m = src.match(/const __iconData = (\{[\s\S]*?\n\});/)
  if (!m) { missing.push(name + " (no literal)"); continue }
  // eslint-disable-next-line no-eval
  const data = eval("(" + m[1] + ")")
  out[name] = { size: data.size || 24, node: data.node }
}

if (missing.length) process.stderr.write("missing: " + missing.join(", ") + "\n")
process.stdout.write(JSON.stringify(out, null, 1))
