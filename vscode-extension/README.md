# git-ai — VS Code extension

Chat with git in plain language, right inside VS Code. Describe what you want and
the AI turns it into a single `git` command — safe ones run automatically,
irreversible ones ask first.

## Features

- 💬 Chat panel in the activity bar (the git-ai icon).
- 🧠 Plain-language → git command (Ollama locally, or any OpenAI-compatible API).
- ✅ Smart commit messages generated from your diff.
- ⚡ Quick buttons: Status, Commit, Pull, Push.
- 🛡️ Safety: blocks destructive shell commands; confirms irreversible git actions.
- 🗣️ After a command, a short plain-language note explains what happened.

## Install (from source)

```bash
cd vscode-extension
npm install -g @vscode/vsce   # one time
vsce package                  # creates git-ai-1.0.0.vsix
```

Then in VS Code: Extensions panel → ⋯ → **Install from VSIX…** → pick the `.vsix`.
Or just press **F5** in this folder to launch an Extension Development Host.

## Configure

Open Settings → search "git-ai":

- **Provider**: `ollama` (offline) or `openai` (cloud).
- **Ollama URL / Model** for local use (needs [Ollama](https://ollama.com)).
- **Base URL / Model / API key** for the cloud. Get a free key at
  [Bynara](https://router.bynara.id/register?ref=NMAP6F9D).

## Usage

Open the **git-ai** icon in the activity bar, open a folder/repo, and type things like:
"commit my changes", "push to GitHub", "what changed?", "create a branch called feature".

---

Created by **Rick Sanchez** (vibe coder). Power by [Noqte](https://noqte.pro).
