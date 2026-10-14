# Hyperspace (widget)

An iOS Home Screen widget, built with [Scriptable](https://scriptable.app), that
shows the same QR code as the [contact page](../hyperspace-contact/) on a black
tile. Tapping the widget opens <https://hyperspace.cutaiar.io>.

`Hyperspace.js` is the whole thing. Setup steps are in the comment at its top:
paste it into a new Scriptable script named "Hyperspace", then add a large
Scriptable widget and point it at that script.

## QR code

`QR_VALUE` is `https://hyperspace.cutaiar.io`, the same payload as
[`hyperspace-contact/qr.svg`](../hyperspace-contact/qr.svg). If the domain
changes, update `SITE_URL` and `QR_VALUE` here along with the contact page.

The image isn't bundled: each widget refresh fetches it from
`api.qrserver.com`, so the widget needs a network connection to render.
