#!/bin/bash
# git-ai launcher for Linux.
# Auto-installs requirements, then starts the graphical app.
cd "$(dirname "$0")" || exit 1

PY="$(command -v python3 || command -v python)"
if [ -z "$PY" ]; then
  echo "Python 3 not found. Install it with your package manager (e.g. sudo apt install python3 python3-tk)."
  exit 1
fi

"$PY" -m pip install --upgrade pip >/dev/null 2>&1
"$PY" -m pip install -r requirements.txt
exec "$PY" git_ai_gui.py
