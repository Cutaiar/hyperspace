# Hyperspace (contact)

A one-page link tree for sharing the project: our two Instagram handles and a QR
code that points back at the page.

**Live: https://hyperspace.cutaiar.io**

`index.html` is the whole page — no build, no dependencies. To change a handle,
edit the two links in it.

## QR code

`qr.svg` is generated once and committed. Regenerate it only if the domain
changes:

```bash
uvx --with qrcode python -c '
import qrcode, qrcode.image.svg
qrcode.make("https://hyperspace.cutaiar.io",
            image_factory=qrcode.image.svg.SvgPathImage).save("qr.svg")'
```

then drop the `width`/`height` attributes so it scales, and add a white
`<rect>` behind the path so it scans on the dark page.

The [Home Screen widget](../hyperspace-ios-widget/) encodes the same URL; update it
too.

## Deployment

Hosted on Vercel as the project `hyperspace-contact` under `cutaiar`, with Root
Directory set to `hyperspace-contact/`, so pushing to `main` deploys. To ship
manually, run `vercel deploy --prod` from the repository root, not this
directory: with a Root Directory set, the CLI looks for `hyperspace-contact/`
inside wherever it runs. The domain `hyperspace.cutaiar.io` (moved here from
the `hyperspace` project) is attached to this project; also served at
`hyperspace-contact.vercel.app`.
A push that changes nothing under `hyperspace-contact/` since the project's last deploy
is skipped: `vercel.json`'s `ignoreCommand` (Vercel's "Ignored Build Step")
diffs this folder against `$VERCEL_GIT_PREVIOUS_SHA` and builds when it
differs, or when there is no earlier deploy to compare with.
Only `main` deploys at all: `git.deploymentEnabled` turns off Vercel's
automatic deploys for every other branch, so a pull request gets no
preview (run `vercel deploy` from the repository root for one).
