# Hyperspace

A 4D polytope viewer in a single HTML file. 18 shapes, from the 5-cell to the
600-cell, rotating through six planes. Audio-reactive: six frequency bands each
drive one plane via a Peak Controller-style transfer chain.

**Live: https://hyperspace-lake.vercel.app**

Or open `hyperspace.html` in a browser — it is one self-contained file with no
build step and no dependencies.

Microphone input needs a secure context, so it works on the deployed site and on
`localhost`, but not from `file://`.
