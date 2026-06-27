# git-ai — an AI-powered git assistant 🤖

A lightweight, **client-side** git assistant. You describe what you want in plain
language, a language model turns it into a `git` command, **safe** commands run
automatically, and only **irreversible** ones ask for a quick confirmation first.

> No API keys or tokens live in this repository. Each user supplies their own in `.env`.

---

## ✨ Features

- Plain-language input → `git` command output
- Two providers: **offline with Ollama** or **any OpenAI-compatible service**
- **Automatic model switching** — prefers your local Ollama, and falls back to the
  cloud provider automatically when Ollama isn't running and a key is set
- Gathers repo context automatically (current branch, status, last 3 commits)
- Multi-layered safety: a **blocked** list and a **dangerous** list with y/n confirmation
- Logs every executed command to `git_ai.log`
- Two interfaces: a **command-line REPL** and a **graphical app (Tkinter)**

### GUI highlights

- **Open Project** — point it at any git folder; all actions run against that repo.
- **Quick actions** — Status, Add All, Fetch, Pull, Push in one click.
- **Easy GitHub login (via `gh`)** — auto-detects your account, lists your repos, clones.
- **Smart commit messages** — the AI writes a subject and body from your **real diff**;
  edit it or hit **Rewrite**, then **Commit** or **Commit & Push**.
- **Settings panel** — paste your Bynara API key, sign up for a key via link, pick a
  cloud model, and switch providers.
- **Ask box** — type any other request in plain language → a safe git command.

---

## 📦 Installation

Requires **Python 3** (with Tkinter for the GUI).

```bash
git clone https://github.com/<YOUR_USERNAME>/git-ai.git
cd git-ai
pip install -r requirements.txt
cp .env.example .env      # then edit .env
```

> macOS note: Apple's system `python3` ships a broken Tk that can crash the GUI.
> Use a python.org build (e.g. `python3.14 git_ai_gui.py`) for the graphical app.

## ⚙️ Configuration (`.env`)

Copy `.env.example` to `.env` and set the values — or just use the in-app **Settings** panel.

### Option 1 — Ollama (local, offline, default)

Nothing leaves your machine.

```env
PROVIDER=ollama
OLLAMA_URL=http://localhost:11434/api/chat
OLLAMA_MODEL=gemma3:4b
```

Requires [Ollama](https://ollama.com) and the model pulled:

```bash
ollama pull gemma3:4b
```

### Option 2 — OpenAI-compatible (cloud)

Any service exposing `/v1/chat/completions`. **Bynara** is an OpenAI-compatible router —
[sign up to get your own key](https://router.bynara.id/register?ref=NMAP6F9D):

```env
PROVIDER=openai
LLM_BASE_URL=https://router.bynara.id/v1
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=your-own-key-here
```

You can paste this key and pick a model directly from the GUI **Settings** panel.

## ▶️ Usage

### Command line (REPL)

```bash
python git_ai.py
```

Type a request, e.g. *"stage everything and commit with message fix bug"*.
Exit with `exit`, `quit`, or `q`. One-shot mode:

```bash
python git_ai.py "show repo status"
```

### Graphical app (Tkinter)

```bash
python git_ai_gui.py
```

## 🛡️ Safety rules

- Only commands starting with `git` are run; everything else is rejected.
- **Blocked (never run):** anything containing `rm`, `sudo`, `mkfs`, writes to `/dev`, fork-bombs, etc.
- **Dangerous (confirm first):** `reset --hard`, `push --force`/`-f`, `clean -f`, `branch -D`,
  `checkout -- <file>`, `restore`, `filter-branch`, `reflog expire`, `gc --prune`, `rebase`,
  `stash drop/clear`, `update-ref -d`.
- `REQUIRE_CONFIRM_FOR_DANGEROUS` (default `True`) controls the confirmation behavior.
- Every executed command is logged to `git_ai.log`.

## 🏗️ Building executables (Windows, macOS & Linux)

GitHub Actions builds executables for **Windows, macOS, and Linux** automatically:

- Every **push to `main`** updates a rolling **"Latest build"** prerelease under **Releases**.
- Every **tag `v*`** creates a full versioned **Release**.
- Every run also uploads per-OS files under **Actions → Artifacts**.

> Note: this is a **desktop** (Tkinter) app, so builds are desktop-only. An Android
> app isn't possible from this codebase without rewriting the UI in a mobile framework.

Build locally:

```bash
pip install pyinstaller
pyinstaller --onefile --name git-ai git_ai.py
pyinstaller --onefile --windowed --name git-ai-gui git_ai_gui.py
```

## 🔑 Why not a shared key?

This project deliberately ships **no shared API key**; each user supplies their own in `.env`.

- **Security:** a shared key in a public repo is leaked and abused instantly.
- **Cost & quota:** OpenAI-compatible services are metered; a shared key burns out fast.
- **Privacy:** with `ollama` you can run fully offline — best for private code.
- **Accountability:** each user owns and is responsible for their own usage.

`.env` is in `.gitignore` and is never committed.

## 📄 License

[MIT](LICENSE)
