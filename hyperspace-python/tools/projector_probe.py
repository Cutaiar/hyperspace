"""Read the projector's battery over ADB (hyperspace/projector.py).

    uv run python tools/projector_probe.py 192.168.1.40           # once: the line and the numbers
    uv run python tools/projector_probe.py 192.168.1.40 --every 30   # a line every 30 s, Ctrl-C ends it

The projector needs network debugging on first (docs/SETUP.md, "The
projector's battery"); the first connect shows an "Allow USB debugging?"
prompt on the projector: tick "Always allow" and accept it with the remote.
"""

import argparse
import time

from hyperspace.projector import PORT, Watch, words


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("host", help="the projector's IPv4 address, or host:port")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--every", type=float, default=0.0, help="seconds between asks; 0 asks once")
    a = ap.parse_args()
    w = Watch(a.host, port=a.port)
    while True:
        r = w.poll()
        print(words(r))
        if r.battery is not None and not a.every:
            b = r.battery
            print(f"  status {b.status}, plugged {', '.join(b.plugged) or 'no'}, "
                  f"present {b.present}, {b.temp_c} °C, {b.volts} V")
        if not a.every:
            return
        time.sleep(a.every)


if __name__ == "__main__":
    main()
