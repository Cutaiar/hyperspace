#!/bin/bash
# Claude Code cloud sessions: the machine CI tests on (.github/workflows/
# tests.yml), so `uv run pytest` and `uv run ruff check .` work as they do
# there. Runs only in a cloud session; on a Mac it does nothing.
#
# - the system libraries CI installs: ALSA headers (python-rtmidi builds
#   from source), PortAudio, Mesa + Xvfb, DejaVu (ui.py's fonts off the
#   Mac), glslang (test_patterns' reference compiler)
# - `uv sync --locked` without the `hands` and `dream` groups — no Ultraleap
#   SDK to build leapc-cffi against, and Linux torch is gigabytes of CUDA.
#   UV_NO_GROUP stays set for the session: `uv run` re-syncs the default
#   groups otherwise, and fails on leapc-cffi
# - a virtual display, :99, for GL and GLFW (CI wraps the run in xvfb-run;
#   a session runs many commands, so it gets one display for all of them)
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

PACKAGES=(libasound2-dev libportaudio2 libgl-dev libgl1-mesa-dri libglx-mesa0
          libegl1 xvfb xauth fonts-dejavu-core glslang-tools)
missing=()
for p in "${PACKAGES[@]}"; do
  dpkg -s "$p" >/dev/null 2>&1 || missing+=("$p")
done
if [ ${#missing[@]} -gt 0 ]; then
  SUDO=""
  [ "$(id -u)" -ne 0 ] && SUDO="sudo"
  export DEBIAN_FRONTEND=noninteractive
  $SUDO apt-get update -q >/dev/null
  $SUDO apt-get install -y -q --no-install-recommends "${missing[@]}" >/dev/null
fi

export UV_NO_GROUP="hands dream"
cd "$CLAUDE_PROJECT_DIR/hyperspace-python"
uv sync --locked

# :99 answers: a server accepts a connection on its socket. Not "an Xvfb
# runs" — one on another display, or a socket a dead server left, is not :99
display_up() {
  python3 -c 'import socket; socket.socket(socket.AF_UNIX).connect("/tmp/.X11-unix/X99")' \
    2>/dev/null
}

if ! display_up; then
  pkill -f '^Xvfb :99( |$)' 2>/dev/null || true          # a :99 server that stopped answering
  # a cached container can keep the lock of a server that is gone
  rm -f /tmp/.X99-lock /tmp/.X11-unix/X99
  setsid nohup Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp >/dev/null 2>&1 &
  for _ in $(seq 50); do
    display_up && break
    sleep 0.1
  done
fi

if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo 'export UV_NO_GROUP="hands dream"' >> "$CLAUDE_ENV_FILE"
  if display_up; then
    echo 'export DISPLAY=:99' >> "$CLAUDE_ENV_FILE"
  else
    echo "session-start: Xvfb did not answer on :99; GL tests need a display" >&2
  fi
fi
