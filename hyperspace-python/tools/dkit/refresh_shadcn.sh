#!/usr/bin/env bash
# Pull the current shadcn components into the prototype, then say what moved.
#
# This is step ZERO of building any component, before the probe and long
# before any Python. The registry is a moving target - `radix-nova` has
# changed its menu treatment, its focus ring and its Combobox's whole shape
# inside this project's lifetime - and a kit measured against a stale vendor
# copy is measured against nothing.
#
#   tools/dkit/refresh_shadcn.sh              # every component the kit uses
#   tools/dkit/refresh_shadcn.sh button input # just these
#
# A clean run prints "no component changed", which is the answer you want and
# is worth the thirty seconds it takes to get. When something HAS changed,
# the diff is the first thing to read: it tells you which measurements are
# now suspect, and those are the ones to re-probe.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP="$HERE/../../../prototypes/dashboard"
cd "$APP"

DEFAULT=(button button-group combobox input select slider switch tooltip
         context-menu scroll-area card badge dialog sheet popover command
         input-group separator dropdown-menu table tabs toggle-group avatar
         skeleton textarea checkbox label kbd)
COMPONENTS=("${@:-${DEFAULT[@]}}")

BEFORE="$(mktemp -d)"
cp -r src/components/ui/. "$BEFORE/"

npx --yes shadcn@latest add "${COMPONENTS[@]}" --overwrite --yes

changed=0
for f in src/components/ui/*.tsx; do
  b="$(basename "$f")"
  if ! diff -q "$BEFORE/$b" "$f" >/dev/null 2>&1; then
    # `"use client"` is inert under Vite and the registry churns it; a file
    # that differs ONLY by that line has not really changed.
    if [ -z "$(diff "$BEFORE/$b" "$f" | grep '^[<>]' | grep -v '"use client"' | tr -d '[:space:]')" ]; then
      continue
    fi
    changed=$((changed + 1))
    echo
    echo "=== $b ==="
    diff -u "$BEFORE/$b" "$f" | sed -n '3,200p'
  fi
done

echo
if [ "$changed" -eq 0 ]; then
  echo "no component changed - the vendored copies were current"
else
  echo "$changed component(s) changed. Re-probe them before trusting any"
  echo "measurement that came out of the old ones:"
  echo "    npm run build && npm run preview -- --port 4173 &"
  echo "    node tools/dkit/probe_react.js 'http://localhost:4173/?probe'"
fi
rm -rf "$BEFORE"
