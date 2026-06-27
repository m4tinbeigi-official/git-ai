#!/bin/bash
# git-ai launcher for macOS (double-click to run).
# Auto-installs requirements, then starts the graphical app.
cd "$(dirname "$0")" || exit 1

# Prefer a python.org build (working Tk) over Apple's system python3.
PY="$(command -v python3.14 || command -v python3.13 || command -v python3.12 || command -v python3 || command -v python)"
if [ -z "$PY" ]; then
  echo "Python 3 not found. Install it from https://www.python.org/downloads/"
  read -r -p "Press Enter to close..."
  exit 1
fi

echo "Using: $PY"
"$PY" -m pip install --upgrade pip >/dev/null 2>&1
"$PY" -m pip install -r requirements.txt
exec "$PY" git_ai_gui.py
