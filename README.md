# Hyperspace

A real-time 4D polytope visualizer. 101 shapes (the 5-cell to the 600-cell and
some forty more 4-polytopes from the grand antiprism to the star polychora, the
Clifford torus, eight surfaces from
the Heart to a Klein bottle, and — plan 28's spike — a catalog of 3D solids,
stars, compounds, mathematical toys and multi-shape scenes, and a vector
logo drawn flat and as capsules), rotating through six planes, with each plane driven by a
frequency band of whatever audio is playing.

This repository holds two iterations, a couple of companions for sharing it,
and a prototype:

- **[`hyperspace-python/`](hyperspace-python/)** — the Python re-platform. Where
  active development happens. See
  [its README](hyperspace-python/README.md) to get started,
  [`docs/SETUP.md`](hyperspace-python/docs/SETUP.md) to set up a Mac, and
  [`docs/ARCHITECTURE.md`](hyperspace-python/docs/ARCHITECTURE.md) for the design.

- **[`hyperspace-web/`](hyperspace-web/)** — the original single-file HTML
  version. No longer under active development, kept for reference and as the
  test oracle for the Python renderer. Live at
  <https://hyperspace-lake.vercel.app> and <https://hyperspacedemo.cutaiar.io>.

- **[`hyperspace-contact/`](hyperspace-contact/)** — a one-page link tree to
  share the project: our Instagram handles and a QR code back to the page. Live
  at <https://hyperspace.cutaiar.io>.

- **[`hyperspace-ios-widget/`](hyperspace-ios-widget/)** — an iOS Home Screen
  widget (a [Scriptable](https://scriptable.app) script) showing the same QR
  code.

- **[`prototypes/edge-lab/`](prototypes/edge-lab/)** — a browser lab for the
  DualSense Edge (plan 42): Chrome reads it over USB or Bluetooth through
  WebHID — every control live, three readouts, the touchpad / shake /
  feedback ideas, and the hardware checks — with a simulator when no pad
  is connected. Not part of the app.

- **[`prototypes/subjects/`](prototypes/subjects/)** — a browser sketch of a
  vector logo as the subject (the Wispr Flow mark), flat or as 3D capsules,
  under a set of materials. Not part of the app; its shapes are, as the
  Flow mark and Flow capsules.

- **[`prototypes/dashboard/`](prototypes/dashboard/)** — a sketch of a
  control surface built from [shadcn/ui](https://ui.shadcn.com) components
  (Vite + React + Tailwind), reading the real shape catalog and band
  routing. A look at that component library, not a proposed UI. Not part
  of the app.
- **[`prototypes/qr-dither/`](prototypes/qr-dither/)** — a tesseract drawn in
  the data of a QR code rather than over one, foldable through 4D with the
  code re-solved every update (0.2 ms a solve) and always scanning to
  `hyperspace.cutaiar.io`. Reed-Solomon is linear, so the picture is the
  payload. Not part of the app.
