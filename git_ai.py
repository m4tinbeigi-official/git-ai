#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
git-ai — an AI-powered git assistant (core).

You describe what you want in plain language; a language model turns it into a
`git` command. Safe commands run automatically; irreversible ones ask for
confirmation first.

This module works both as a command-line REPL and as a shared library used by
the graphical interface (git_ai_gui.py).

Two providers (read from .env):
  - ollama : a local, offline model (default gemma3:4b) — nothing leaves your machine.
  - openai : any OpenAI-compatible service (/v1/chat/completions) with your own
             base_url and API key.

No keys or tokens are stored in this code. Each user supplies their own in .env.
"""

import os
import re
import sys
import json
import subprocess
from datetime import datetime

import requests

# ---------------------------------------------------------------------------
# Load .env (skip silently if python-dotenv is not installed)
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROVIDER = os.getenv("PROVIDER", "ollama").strip().lower()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat").strip()
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b").strip()

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://router.bynara.id/v1").strip().rstrip("/")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini").strip()
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()

# Bynara is an OpenAI-compatible router. Sign up (with referral) to get a key.
BYNARA_BASE_URL = "https://router.bynara.id/v1"
BYNARA_SIGNUP_URL = "https://router.bynara.id/register?ref=NMAP6F9D"

# When True, dangerous commands require a y/n confirmation before running.
REQUIRE_CONFIRM_FOR_DANGEROUS = True

LOG_FILENAME = "git_ai.log"
REQUEST_TIMEOUT = 120     # seconds
MAX_DIFF_CHARS = 6000     # cap the diff length sent to the model

# ---------------------------------------------------------------------------
# Safety rules
# ---------------------------------------------------------------------------
BLOCKED_PATTERNS = [
    r"\brm\b", r"\bsudo\b", r"\bmkfs\b", r">\s*/dev/",
    r":\(\)\s*\{", r"\bdd\b\s+if=", r"\bshutdown\b", r"\breboot\b",
]

DANGEROUS_PATTERNS = [
    r"reset\s+--hard", r"push\s+.*--force", r"push\s+.*\s-f\b", r"push\s+-f\b",
    r"clean\s+-[a-z]*f", r"branch\s+-D\b", r"checkout\s+--\s", r"\brestore\b",
    r"filter-branch", r"reflog\s+expire", r"gc\s+.*--prune", r"\brebase\b",
    r"stash\s+(drop|clear)", r"update-ref\s+-d",
]

# ---------------------------------------------------------------------------
# System prompt — turn natural language into a git command
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are a git command-line assistant.
The user describes, in plain language, what they want to do. You must turn it
into a single, complete, valid `git` command.

Rules:
- Return ONLY a valid JSON object. No extra text, no code fences.
- The exact shape must be:
  {"command": "<full git command>", "explanation": "<short explanation>"}
- "command" must always start with the word git.
- If the request is ambiguous, pick the most likely git command.

Examples:
User: stage everything and commit with message "fix bug"
Output: {"command": "git add -A && git commit -m \\"fix bug\\"", "explanation": "Stages all changes and commits them."}
User: push the current branch to origin
Output: {"command": "git push origin HEAD", "explanation": "Pushes the current branch to origin."}
User: show me the repo status
Output: {"command": "git status", "explanation": "Shows the current repository status."}
"""

# System prompt — write a commit message from a diff
COMMIT_MSG_SYSTEM_PROMPT = """You write git commit messages.
Given the staged changes (diff and status), write a clean, meaningful commit message.

Rules:
- Return ONLY a valid JSON object:
  {"title": "<short imperative subject line, <= ~72 chars>", "description": "<optional multi-line body explaining what and why>"}
- Write the title in Conventional Commits style (e.g. feat: ..., fix: ..., docs: ...).
- For tiny changes the description may be empty ("").
- Match the project's dominant language; default to English.
"""


# ---------------------------------------------------------------------------
# Git helper commands
# ---------------------------------------------------------------------------
def run_git_context_cmd(args, cwd=None):
    """Run a command and return its stdout (used for gathering context)."""
    try:
        out = subprocess.run(args, capture_output=True, text=True, timeout=20, cwd=cwd)
        return (out.stdout or "").strip()
    except Exception:
        return ""


def get_branch(cwd=None):
    return run_git_context_cmd(["git", "branch", "--show-current"], cwd)


def gather_repo_context(cwd=None):
    """Collect the current branch, short status, and last three commits."""
    branch = get_branch(cwd)
    status = run_git_context_cmd(["git", "status", "--short"], cwd)
    log = run_git_context_cmd(["git", "log", "--oneline", "-3"], cwd)
    return (
        "Current repository context:\n"
        f"Current branch: {branch or '(unknown / not a git repo)'}\n"
        f"Short status:\n{status or '(no changes)'}\n"
        f"Last 3 commits:\n{log or '(no commits)'}"
    )


def extract_json(text):
    """Robust JSON parsing: whole text first, then the first {...} block via regex."""
    text = (text or "").strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    raise ValueError("The model did not return valid JSON.")


# ---------------------------------------------------------------------------
# Model calls
# ---------------------------------------------------------------------------
def call_ollama(user_content, system_prompt=SYSTEM_PROMPT):
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "stream": False,
        "format": "json",
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    content = resp.json().get("message", {}).get("content", "")
    return extract_json(content)


def call_openai(user_content, system_prompt=SYSTEM_PROMPT):
    if not LLM_API_KEY:
        raise RuntimeError("LLM_API_KEY is not set. Put it in your .env file.")
    url = f"{LLM_BASE_URL}/chat/completions"
    headers = {"Authorization": f"Bearer {LLM_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    return extract_json(content)


def ollama_reachable():
    """Quick check whether a local Ollama server is responding."""
    try:
        base = OLLAMA_URL.split("/api/")[0]
        requests.get(f"{base}/api/tags", timeout=3)
        return True
    except Exception:
        return False


def active_provider():
    """Decide which provider to actually use, with automatic switching.

    - If PROVIDER is 'openai', use it.
    - If PROVIDER is 'ollama' but the local server is unreachable and an API key
      is configured, automatically fall back to the OpenAI-compatible provider.
    """
    if PROVIDER == "openai":
        return "openai"
    if not ollama_reachable() and LLM_API_KEY:
        return "openai"
    return "ollama"


def list_openai_models():
    """List models available from the OpenAI-compatible router (needs a key)."""
    if not LLM_API_KEY:
        return []
    try:
        r = requests.get(
            f"{LLM_BASE_URL}/models",
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json().get("data", [])
        return sorted([m.get("id") for m in data if m.get("id")])
    except Exception:
        return []


def _ask(user_content, system_prompt=SYSTEM_PROMPT):
    if active_provider() == "openai":
        return call_openai(user_content, system_prompt)
    return call_ollama(user_content, system_prompt)


def ask_model(user_prompt, cwd=None):
    """Natural-language request -> {command, explanation}."""
    context = gather_repo_context(cwd)
    return _ask(f"{context}\n\nUser request: {user_prompt}")


def generate_commit_message(cwd=None, hint=""):
    """Generate a commit message from the staged (or working) changes.
    Returns {"title": str, "description": str}.
    """
    diff = run_git_context_cmd(["git", "diff", "--staged"], cwd)
    if not diff:
        # Nothing staged: fall back to the working-tree diff.
        diff = run_git_context_cmd(["git", "diff"], cwd)
    status = run_git_context_cmd(["git", "status", "--short"], cwd)

    if not diff and not status:
        raise ValueError("No changes found to base a commit message on.")

    if len(diff) > MAX_DIFF_CHARS:
        diff = diff[:MAX_DIFF_CHARS] + "\n... (truncated)"

    user_content = (
        f"File status:\n{status or '(unknown)'}\n\n"
        f"Changes (diff):\n{diff or '(no diff available)'}"
    )
    if hint:
        user_content += f"\n\nUser hint for the message: {hint}"

    result = _ask(user_content, COMMIT_MSG_SYSTEM_PROMPT)
    return {
        "title": (result.get("title") or "").strip(),
        "description": (result.get("description") or "").strip(),
    }


# ---------------------------------------------------------------------------
# GitHub CLI (gh) helpers — used by the GUI
# ---------------------------------------------------------------------------
def gh_available():
    """Is the gh tool installed?"""
    try:
        subprocess.run(["gh", "--version"], capture_output=True, text=True, timeout=10)
        return True
    except Exception:
        return False


def gh_account():
    """Return the logged-in GitHub username, or None."""
    try:
        out = subprocess.run(
            ["gh", "auth", "status"], capture_output=True, text=True, timeout=15
        )
        text = (out.stdout or "") + (out.stderr or "")
        m = re.search(r"account\s+([A-Za-z0-9-]+)", text)
        if not m:
            m = re.search(r"Logged in to github\.com as ([A-Za-z0-9-]+)", text)
        return m.group(1) if m else None
    except Exception:
        return None


def gh_list_repos(limit=200):
    """Return the user's repositories (nameWithOwner)."""
    try:
        out = subprocess.run(
            ["gh", "repo", "list", "--limit", str(limit),
             "--json", "nameWithOwner", "--jq", ".[].nameWithOwner"],
            capture_output=True, text=True, timeout=30,
        )
        return [l.strip() for l in (out.stdout or "").splitlines() if l.strip()]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Settings (.env) management — used by the GUI Settings panel
# ---------------------------------------------------------------------------
def find_env_path():
    """Path to the .env file next to this script."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")


def apply_config(values):
    """Update the in-memory configuration globals at runtime."""
    global PROVIDER, LLM_BASE_URL, LLM_MODEL, LLM_API_KEY, OLLAMA_URL, OLLAMA_MODEL
    if "PROVIDER" in values:
        PROVIDER = values["PROVIDER"].strip().lower()
    if "LLM_BASE_URL" in values:
        LLM_BASE_URL = values["LLM_BASE_URL"].strip().rstrip("/")
    if "LLM_MODEL" in values:
        LLM_MODEL = values["LLM_MODEL"].strip()
    if "LLM_API_KEY" in values:
        LLM_API_KEY = values["LLM_API_KEY"].strip()
    if "OLLAMA_URL" in values:
        OLLAMA_URL = values["OLLAMA_URL"].strip()
    if "OLLAMA_MODEL" in values:
        OLLAMA_MODEL = values["OLLAMA_MODEL"].strip()


def update_env(values):
    """Persist key=value pairs to .env (preserving existing keys) and apply them."""
    path = find_env_path()
    data, order = {}, []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if s and not s.startswith("#") and "=" in s:
                    k, v = s.split("=", 1)
                    if k not in data:
                        order.append(k)
                    data[k] = v
    for k, v in values.items():
        if k not in data:
            order.append(k)
        data[k] = v
    with open(path, "w", encoding="utf-8") as f:
        for k in order:
            f.write(f"{k}={data[k]}\n")
    apply_config(values)
    return path


# ---------------------------------------------------------------------------
# Safety and execution
# ---------------------------------------------------------------------------
def classify_command(command):
    """Classify a command: 'blocked' | 'invalid' | 'dangerous' | 'safe'."""
    cmd = (command or "").strip()
    if not cmd:
        return "invalid", "No command was produced."
    if not cmd.startswith("git"):
        return "invalid", "Only commands starting with git are allowed."
    for pat in BLOCKED_PATTERNS:
        if re.search(pat, cmd):
            return "blocked", f"Command blocked (dangerous pattern: {pat})."
    for pat in DANGEROUS_PATTERNS:
        if re.search(pat, cmd):
            return "dangerous", f"This command is irreversible or risky (pattern: {pat})."
    return "safe", "safe"


def log_command(command, cwd=None):
    """Append the executed command, with a timestamp, to git_ai.log in the repo."""
    try:
        path = os.path.join(cwd or os.getcwd(), LOG_FILENAME)
        with open(path, "a", encoding="utf-8") as f:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{ts}] {command}\n")
    except Exception:
        pass


def run_command_capture(command, cwd=None):
    """Run a command and return combined stdout+stderr as text (used by the GUI)."""
    log_command(command, cwd)
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=cwd)
        out = (result.stdout or "") + (result.stderr or "")
        if result.returncode != 0:
            out += f"\nExit code: {result.returncode}"
        return out.strip() or "(no output)"
    except Exception as e:
        return f"Error running command: {e}"


def execute_command(command, cwd=None):
    """Run a git command and print its output (used by the CLI)."""
    log_command(command, cwd)
    try:
        result = subprocess.run(command, shell=True, text=True, cwd=cwd)
        if result.returncode != 0:
            print(f"Command exited with code {result.returncode}.")
    except Exception as e:
        print(f"Error running command: {e}")


# ---------------------------------------------------------------------------
# CLI flow
# ---------------------------------------------------------------------------
def confirm(prompt):
    try:
        ans = input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return ans in ("y", "yes")


def handle_request(user_prompt):
    try:
        result = ask_model(user_prompt)
    except requests.exceptions.ConnectionError:
        if PROVIDER == "openai":
            print(f"Could not connect to the server. Check base_url: {LLM_BASE_URL}")
        else:
            print(f"Could not connect to Ollama. Is it running at {OLLAMA_URL}?")
        return
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response is not None else "?"
        if code in (401, 403):
            print("Invalid API key or no access (authentication error).")
        else:
            print(f"Server error (code {code}).")
        return
    except RuntimeError as e:
        print(f"Error: {e}")
        return
    except ValueError as e:
        print(f"Error: {e}")
        return
    except Exception as e:
        print(f"Unexpected error: {e}")
        return

    command = (result.get("command") or "").strip()
    explanation = (result.get("explanation") or "").strip()
    print(f"\nSuggested command: {command}")
    if explanation:
        print(f"  Explanation: {explanation}")

    kind, msg = classify_command(command)
    if kind in ("invalid", "blocked"):
        print(f"Not executed: {msg}")
        return
    if kind == "dangerous":
        print(f"Warning: {msg}")
        if REQUIRE_CONFIRM_FOR_DANGEROUS and not confirm("Are you sure? Run it? (y/n): "):
            print("Cancelled.")
            return
        execute_command(command)
        return
    print("Running...")
    execute_command(command)


EXIT_WORDS = {"exit", "quit", "q"}


def repl():
    print("=" * 60)
    print("  git-ai — an AI-powered git assistant")
    if PROVIDER == "openai":
        print(f"  provider: openai  |  model: {LLM_MODEL}  |  {LLM_BASE_URL}")
    else:
        print(f"  provider: ollama  |  model: {OLLAMA_MODEL}  |  {OLLAMA_URL}")
    print("  To exit: exit / quit / q")
    print("=" * 60)
    while True:
        try:
            user_prompt = input("\nWhat do you want to do? ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break
        if not user_prompt:
            continue
        if user_prompt.lower() in EXIT_WORDS:
            print("Bye!")
            break
        handle_request(user_prompt)


def main():
    if len(sys.argv) > 1:
        handle_request(" ".join(sys.argv[1:]))
        return
    repl()


if __name__ == "__main__":
    main()
