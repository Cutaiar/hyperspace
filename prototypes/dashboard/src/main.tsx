import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import "./index.css"
import App from "./App.tsx"
import Gallery from "./Gallery.tsx"
import Probe from "./Probe.tsx"

// ?gallery swaps the dashboard for the dkit diff grid, ?probe for the
// measuring route. No router: the harness only ever loads one URL.
const q = new URLSearchParams(location.search)

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {q.has("probe") ? (
      <Probe dark={q.has("dark")} open={q.has("open")} />
    ) : q.has("gallery") ? (
      <Gallery withText={q.has("text")} dark={q.has("dark")} />
    ) : (
      <App />
    )}
  </StrictMode>
)
