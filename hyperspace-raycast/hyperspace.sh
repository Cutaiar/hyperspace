#!/bin/bash

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Hyperspace
# @raycast.mode compact

# Optional parameters:
# @raycast.icon 🌌
# @raycast.packageName Hyperspace
# @raycast.argument1 { "type": "dropdown", "placeholder": "Mode", "optional": true, "data": [{ "title": "Rig (projector)", "value": "rig" }, { "title": "Laptop (one screen)", "value": "laptop" }] }

# Documentation:
# @raycast.description Launch the Hyperspace render + control windows. Focuses the existing instance if one is already running.
# @raycast.author Dillon Cutaiar

# The app, in one command from Raycast. See README.md next to this file.

# Where the app is: the sibling of this script's own directory when Raycast
# reads the repo copy (symlinks resolved), else the usual checkout.
SELF="$0"
while [ -L "$SELF" ]; do SELF="$(readlink "$SELF")"; done
HERE="$(cd "$(dirname "$SELF")" && pwd)"
REPO="$HERE/../hyperspace-python"
[ -d "$REPO" ] || REPO="$HOME/Dev/hyperspace/hyperspace-python"

# Raycast runs scripts with a bare PATH, so uv is named in full.
UV="/opt/homebrew/bin/uv"
LOG="$HOME/Hyperspace/launch.log"

# Already up? Bring it forward rather than starting a second process.
PID=$(pgrep -f "bin/hyperspace" | head -1)
if [ -n "$PID" ]; then
  osascript -e "tell application \"System Events\" to set frontmost of (first process whose unix id is $PID) to true" >/dev/null 2>&1
  echo "Already running (pid $PID)"
  exit 0
fi

[ -x "$UV" ] || { echo "uv not found at $UV — brew install uv"; exit 1; }
[ -d "$REPO" ] || { echo "Repo not found at $REPO"; exit 1; }

ARGS=()
[ "$1" = "laptop" ] && ARGS+=(--laptop)

mkdir -p "$(dirname "$LOG")"
echo "--- $(date '+%Y-%m-%d %H:%M:%S') start ${ARGS[*]:-(rig)} ---" >> "$LOG"

# Detached: Raycast would otherwise sit waiting on the app's whole run.
cd "$REPO" || exit 1
nohup "$UV" run hyperspace "${ARGS[@]}" >> "$LOG" 2>&1 &
disown

echo "Hyperspace starting${ARGS[*]:+ (laptop)}"
