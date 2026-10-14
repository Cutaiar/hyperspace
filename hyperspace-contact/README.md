# Hyperspace (contact)

A one-page link tree for sharing the project: our two Instagram handles and a QR
code that points back at the page.

**Live: https://hyperspace-contact.cutaiar.io**

`index.html` is the whole page — no build, no dependencies. To change a handle,
edit the two links in it.

## QR code

`qr.svg` is generated once and committed. Regenerate it only if the domain
changes:

```bash
uvx --with qrcode python -c '
import qrcode, qrcode.image.svg
qrcode.make("https://hyperspace-contact.cutaiar.io",
            image_factory=qrcode.image.svg.SvgPathImage).save("qr.svg")'
```

then drop the `width`/`height` attributes so it scales, and add a white
`<rect>` behind the path so it scans on the dark page.

## Deployment

Hosted on Vercel as the project `hyperspace-contact` under `cutaiar`, with Root
Directory set to `hyperspace-contact/`, so pushing to `main` deploys;
`vercel deploy --prod` from this directory ships manually. The domain
`hyperspace-contact.cutaiar.io` is attached to the project.
