#!/bin/zsh
# SC3a spike: the pacing shapes, in rounds so the shared Mac's noise shows.
# From hyperspace-python/: tools/sc3a_spike_pacing.sh [rounds] [secs]
rounds=${1:-3}
secs=${2:-20}
run() { .venv/bin/python tools/sc3a_spike.py pacing "$@" --secs "$secs" 2>&1 | grep -v Persistence; }
for r in $(seq 1 "$rounds"); do
  echo "# round $r $(uptime)"
  run --shape today --mon 0
  run --shape presenter-vsync --mon 0
  run --shape today --mon 2
  run --shape presenter-vsync --mon 2
  run --shape hidden-timer
  run --shape hidden-only-timer
  run --shape two-vsync --mon 0 --mon2 2
  run --shape occluded --mon 0
  run --shape guarded --mon 0
  run --shape guarded --mon 2
done
