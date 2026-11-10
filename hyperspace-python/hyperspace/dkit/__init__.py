"""dkit: the measured shadcn kit, as a package the panel imports.

Its home for everything that is not the runtime — the tests, the gallery
and the dashboard, the browser oracles and the pixel diff, the docs
(README, ROADMAP, HANDOFF, RETRO) — is still `tools/dkit/`, where each of
these modules keeps a one-line alias so the kit's own tools import it by
its bare name. Hyperspace imports it through `hyperspace.ui_kit`.
"""
