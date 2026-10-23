"""Media sources (plan 32): stills, video files and live feeds as RGBA
frames the renderer can put on a channel. This package is the foundation —
the frame type, source ids, the worker pool and still images. Nothing here
decodes, resizes or blocks on the frame thread: jobs that end go to
`pool.submit`, blocking reads live on a source's own thread. Each adapter
library (av, pillow_heif, syphon, cyndilib) is imported inside the function
that opens a source, so importing `hyperspace.app` pulls none of them."""
