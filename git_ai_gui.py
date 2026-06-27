#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
git-ai — graphical interface (Tkinter).

Features:
  - Open any git repository folder; every action runs against that project.
  - Quick git buttons: Status, Add All, Fetch, Pull, Push.
  - Easy GitHub login via `gh`: auto-detects your account, lists your repos, clones.
  - Smart commit messages: the AI writes a subject and body from your real diff;
    edit it by hand or hit "Rewrite". Then Commit, or Commit & Push.
  - Ask box: type any request in plain language -> a safe git command.

Uses the git_ai core. No keys or tokens live in this code.
"""

import os
import re
import threading
import webbrowser
import subprocess
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog

import git_ai as core

# --- palette -------------------------------------------------------------
BG      = "#f4f5f7"
CARD    = "#ffffff"
INK     = "#1f2328"
MUTED   = "#6e7781"
ACCENT  = "#2563eb"
OK      = "#1a7f37"
DANGER  = "#cf222e"
CONSOLE_BG = "#0d1117"
CONSOLE_FG = "#d1d5da"


class GitAIApp:
    def __init__(self, root):
        self.root = root
        self.repo_path = None
        root.title("git-ai")
        root.geometry("860x700")
        root.minsize(720, 600)
        root.configure(bg=BG)

        self._init_style()
        self._build_header()

        body = ttk.Frame(root, style="App.TFrame", padding=(14, 6, 14, 12))
        body.pack(fill="both", expand=True)

        self._build_repo(body)
        self._build_github(body)
        self._build_actions(body)
        self._build_commit(body)
        self._build_ask(body)
        self._build_console(body)

        self.log("Welcome to git-ai. Start by opening a project.")
        self.refresh_github_status()

    # ------------------------------------------------------------- styling
    def _init_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("App.TFrame", background=BG)
        style.configure("Card.TLabelframe", background=CARD, relief="flat",
                        borderwidth=1, bordercolor="#d0d7de")
        style.configure("Card.TLabelframe.Label", background=BG, foreground=MUTED,
                        font=("Helvetica", 10, "bold"))
        style.configure("Card.TFrame", background=CARD)
        style.configure("Muted.TLabel", background=CARD, foreground=MUTED,
                        font=("Helvetica", 10))
        style.configure("Body.TLabel", background=CARD, foreground=INK,
                        font=("Helvetica", 10))
        style.configure("Branch.TLabel", background=CARD, foreground=OK,
                        font=("Helvetica", 10, "bold"))
        style.configure("TButton", font=("Helvetica", 10), padding=(10, 5))
        style.configure("Primary.TButton", font=("Helvetica", 10, "bold"))
        style.map("Primary.TButton",
                  background=[("!disabled", ACCENT), ("active", "#1d4ed8")],
                  foreground=[("!disabled", "#ffffff")])
        style.configure("TEntry", padding=4)
        style.configure("TCombobox", padding=4)

    def _build_header(self):
        bar = tk.Frame(self.root, bg=INK, height=52)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        tk.Label(bar, text="git-ai", bg=INK, fg="#ffffff",
                 font=("Helvetica", 16, "bold")).pack(side="left", padx=16)
        tk.Label(bar, text="AI-powered git assistant", bg=INK, fg="#9aa4af",
                 font=("Helvetica", 10)).pack(side="left")
        tk.Button(bar, text="⚙ Settings", command=self.open_settings,
                  bg=INK, fg="#ffffff", activebackground="#30363d",
                  activeforeground="#ffffff", relief="flat", bd=0,
                  font=("Helvetica", 10), cursor="hand2").pack(side="right", padx=12)
        self.model_badge = tk.Label(bar, text="", bg=INK, fg="#9aa4af",
                                    font=("Helvetica", 10))
        self.model_badge.pack(side="right", padx=4)
        self._refresh_badge()

    def _refresh_badge(self):
        mode = core.PROVIDER
        model = core.LLM_MODEL if mode == "openai" else core.OLLAMA_MODEL
        self.model_badge.config(text=f"{mode} · {model}")

    def _card(self, parent, title):
        lf = ttk.Labelframe(parent, text=title, style="Card.TLabelframe", padding=10)
        lf.pack(fill="x", pady=6)
        inner = ttk.Frame(lf, style="Card.TFrame")
        inner.pack(fill="x")
        return inner

    # ------------------------------------------------------------- sections
    def _build_repo(self, parent):
        c = self._card(parent, "Repository")
        ttk.Button(c, text="Open Project…", command=self.choose_repo).pack(side="left")
        self.repo_label = ttk.Label(c, text="No project opened", style="Muted.TLabel")
        self.repo_label.pack(side="left", padx=10, fill="x", expand=True)
        self.branch_label = ttk.Label(c, text="", style="Branch.TLabel")
        self.branch_label.pack(side="right")

    def _build_github(self, parent):
        c = self._card(parent, "GitHub")
        self.gh_status = ttk.Label(c, text="Checking…", style="Muted.TLabel")
        self.gh_status.pack(side="left", fill="x", expand=True)
        ttk.Button(c, text="Login", command=self.github_login).pack(side="left", padx=3)
        ttk.Button(c, text="Fetch Repos", command=self.fetch_repos).pack(side="left", padx=3)
        self.repo_combo = ttk.Combobox(c, width=28, state="readonly")
        self.repo_combo.pack(side="left", padx=3)
        ttk.Button(c, text="Clone", command=self.clone_selected).pack(side="left", padx=3)

    def _build_actions(self, parent):
        c = self._card(parent, "Quick Actions")
        for text, cmd in [
            ("Status", lambda: self.git("git status")),
            ("Add All", lambda: self.git("git add -A")),
            ("Fetch", lambda: self.git("git fetch")),
            ("Pull", lambda: self.git("git pull")),
            ("Push", self.do_push),
        ]:
            ttk.Button(c, text=text, width=10, command=cmd).pack(side="left", padx=3)

    def _build_commit(self, parent):
        c = self._card(parent, "Smart Commit")
        row = ttk.Frame(c, style="Card.TFrame")
        row.pack(fill="x")
        ttk.Label(row, text="Subject", style="Body.TLabel", width=8).pack(side="left")
        self.commit_title = ttk.Entry(row, font=("Helvetica", 11))
        self.commit_title.pack(side="left", fill="x", expand=True, padx=(4, 0))

        ttk.Label(c, text="Body", style="Body.TLabel").pack(anchor="w", pady=(8, 2))
        self.commit_desc = tk.Text(c, height=4, font=("Helvetica", 10), wrap="word",
                                   relief="solid", borderwidth=1,
                                   highlightthickness=0, bg="#fbfcfd")
        self.commit_desc.pack(fill="x")

        row2 = ttk.Frame(c, style="Card.TFrame")
        row2.pack(fill="x", pady=(8, 0))
        ttk.Button(row2, text="✨ Generate with AI",
                   command=lambda: self.gen_commit_msg(False)).pack(side="left", padx=3)
        ttk.Button(row2, text="Rewrite",
                   command=lambda: self.gen_commit_msg(True)).pack(side="left", padx=3)
        ttk.Button(row2, text="Commit", command=self.do_commit).pack(side="left", padx=3)
        ttk.Button(row2, text="Commit & Push", style="Primary.TButton",
                   command=self.do_commit_push).pack(side="left", padx=3)

    def _build_ask(self, parent):
        c = self._card(parent, "Ask in Plain Language")
        self.ask_entry = ttk.Entry(c, font=("Helvetica", 11))
        self.ask_entry.pack(side="left", fill="x", expand=True)
        self.ask_entry.bind("<Return>", lambda e: self.ask_submit())
        self.ask_btn = ttk.Button(c, text="Run", style="Primary.TButton",
                                  width=10, command=self.ask_submit)
        self.ask_btn.pack(side="left", padx=(6, 0))

    def _build_console(self, parent):
        wrap = ttk.Labelframe(parent, text="Console", style="Card.TLabelframe", padding=2)
        wrap.pack(fill="both", expand=True, pady=6)
        self.console = scrolledtext.ScrolledText(
            wrap, font=("Menlo", 10), wrap="word", height=10,
            bg=CONSOLE_BG, fg=CONSOLE_FG, insertbackground=CONSOLE_FG,
            relief="flat", borderwidth=0, padx=10, pady=8,
        )
        self.console.pack(fill="both", expand=True)
        self.console.configure(state="disabled")

    # -------------------------------------------------------------- helpers
    def log(self, text):
        self.console.configure(state="normal")
        self.console.insert("end", text + "\n")
        self.console.see("end")
        self.console.configure(state="disabled")

    def require_repo(self):
        if not self.repo_path:
            messagebox.showwarning("No project", "Open a git repository first.")
            return False
        return True

    def refresh_branch(self):
        if self.repo_path:
            b = core.get_branch(self.repo_path)
            self.branch_label.config(text=(f"⎇ {b}" if b else "(not a git repo)"))

    # ----------------------------------------------------------- repo logic
    def choose_repo(self):
        path = filedialog.askdirectory(title="Open project folder")
        if not path:
            return
        self.repo_path = path
        self.repo_label.config(text=path)
        if not os.path.isdir(os.path.join(path, ".git")):
            self.log("Note: this folder is not a git repo yet. You can run 'git init'.")
        self.refresh_branch()
        self.log(f"Project opened: {path}")

    # --------------------------------------------------------- git commands
    def git(self, command, dangerous_ok=False):
        if not self.require_repo():
            return
        kind, msg = core.classify_command(command)
        if kind in ("invalid", "blocked"):
            self.log(f"Not executed: {msg}")
            return
        if kind == "dangerous" and not dangerous_ok and core.REQUIRE_CONFIRM_FOR_DANGEROUS:
            if not messagebox.askyesno("Confirm dangerous command", f"{command}\n\n{msg}\n\nRun it?"):
                self.log("Cancelled.")
                return
        self.log(f"$ {command}")
        out = core.run_command_capture(command, cwd=self.repo_path)
        self.log(out + "\n")
        self.refresh_branch()

    def do_push(self):
        if not self.require_repo():
            return
        branch = core.get_branch(self.repo_path) or "HEAD"
        self.git(f"git push -u origin {branch}")

    def do_commit(self):
        if not self.require_repo():
            return
        title = self.commit_title.get().strip()
        desc = self.commit_desc.get("1.0", "end").strip()
        if not title:
            messagebox.showwarning("Empty subject", "Enter a commit subject or generate one with AI.")
            return
        cmd = f'git commit -m "{title.replace(chr(34), chr(92) + chr(34))}"'
        if desc:
            cmd += f' -m "{desc.replace(chr(34), chr(92) + chr(34))}"'
        self.log(f"$ {cmd}")
        out = core.run_command_capture(cmd, cwd=self.repo_path)
        self.log(out + "\n")
        self.refresh_branch()

    def do_commit_push(self):
        self.do_commit()
        self.do_push()

    # ---------------------------------------------------- AI commit message
    def gen_commit_msg(self, rewrite):
        if not self.require_repo():
            return
        hint = ""
        if rewrite:
            hint = (self.commit_title.get().strip() + " " +
                    self.commit_desc.get("1.0", "end").strip()).strip()
        self.log("Generating commit message from your changes…")
        threading.Thread(target=self._gen_worker, args=(hint,), daemon=True).start()

    def _gen_worker(self, hint):
        try:
            result = core.generate_commit_message(cwd=self.repo_path, hint=hint)
        except Exception as e:
            self.root.after(0, lambda: self.log(f"Error: {e}\n"))
            return
        self.root.after(0, lambda: self._fill_commit(result))

    def _fill_commit(self, result):
        self.commit_title.delete(0, "end")
        self.commit_title.insert(0, result.get("title", ""))
        self.commit_desc.delete("1.0", "end")
        self.commit_desc.insert("1.0", result.get("description", ""))
        self.log("Commit message ready. Edit if needed, then Commit.\n")

    # ----------------------------------------------------------- GitHub (gh)
    def refresh_github_status(self):
        threading.Thread(target=self._gh_status_worker, daemon=True).start()

    def _gh_status_worker(self):
        if not core.gh_available():
            self.root.after(0, lambda: self.gh_status.config(
                text="GitHub CLI (gh) not installed — get it at cli.github.com", foreground=DANGER))
            return
        acct = core.gh_account()
        if acct:
            self.root.after(0, lambda: self.gh_status.config(
                text=f"Signed in as {acct}", foreground=OK))
        else:
            self.root.after(0, lambda: self.gh_status.config(
                text="Not signed in — click Login", foreground=DANGER))

    def github_login(self):
        if not core.gh_available():
            messagebox.showinfo("gh not installed", "Install GitHub CLI from cli.github.com first.")
            return
        self.log("Starting GitHub login…")
        threading.Thread(target=self._gh_login_worker, daemon=True).start()

    def _gh_login_worker(self):
        try:
            proc = subprocess.Popen(
                ["gh", "auth", "login", "--web", "--git-protocol", "https", "--hostname", "github.com"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            )
            try:
                proc.stdin.write("\n")  # skip the "Press Enter to open…" prompt
                proc.stdin.flush()
            except Exception:
                pass
            code = None
            for line in iter(proc.stdout.readline, ""):
                line = line.strip()
                m = re.search(r"one-time code:?\s*([A-Z0-9-]{6,})", line)
                if m and not code:
                    code = m.group(1)
                    self.root.after(0, lambda c=code: self._show_code(c))
            proc.wait(timeout=300)
        except Exception as e:
            self.root.after(0, lambda: self.log(f"Login error: {e}"))
        finally:
            self.root.after(0, self.refresh_github_status)
            self.root.after(0, lambda: self.log("Login flow finished; status refreshed."))

    def _show_code(self, code):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(code)
        except Exception:
            pass
        self.log(f"One-time code: {code}  (copied to clipboard)")
        webbrowser.open("https://github.com/login/device")
        messagebox.showinfo(
            "GitHub login code",
            f"This code was copied to your clipboard:\n\n{code}\n\n"
            "Enter it in the opened browser, then Authorize.",
        )

    def fetch_repos(self):
        if not core.gh_account():
            messagebox.showinfo("Login required", "Sign in to GitHub first.")
            return
        self.log("Fetching repositories…")
        threading.Thread(target=self._fetch_worker, daemon=True).start()

    def _fetch_worker(self):
        repos = core.gh_list_repos()
        def update():
            self.repo_combo["values"] = repos
            if repos:
                self.repo_combo.current(0)
                self.log(f"Fetched {len(repos)} repositories.\n")
            else:
                self.log("No repositories found.\n")
        self.root.after(0, update)

    def clone_selected(self):
        repo = self.repo_combo.get().strip()
        if not repo:
            messagebox.showinfo("Select a repo", "Pick a repository from the list first.")
            return
        dest = filedialog.askdirectory(title="Choose a destination folder")
        if not dest:
            return
        self.log(f"Cloning {repo} …")
        threading.Thread(target=self._clone_worker, args=(repo, dest), daemon=True).start()

    def _clone_worker(self, repo, dest):
        out = core.run_command_capture(f"gh repo clone {repo}", cwd=dest)
        cloned = os.path.join(dest, repo.split("/")[-1])
        def update():
            self.log(out + "\n")
            if os.path.isdir(os.path.join(cloned, ".git")):
                self.repo_path = cloned
                self.repo_label.config(text=cloned)
                self.refresh_branch()
                self.log(f"Project set to cloned repo: {cloned}\n")
        self.root.after(0, update)

    # ------------------------------------------------------- ask (NL) box
    def ask_submit(self):
        if not self.require_repo():
            return
        prompt = self.ask_entry.get().strip()
        if not prompt:
            return
        self.ask_entry.delete(0, "end")
        self.log(f"> {prompt}")
        self.ask_btn.config(state="disabled")
        threading.Thread(target=self._ask_worker, args=(prompt,), daemon=True).start()

    def _ask_worker(self, prompt):
        try:
            result = core.ask_model(prompt, cwd=self.repo_path)
        except Exception as e:
            self.root.after(0, lambda: self._ask_done(str(e)))
            return
        self.root.after(0, lambda: self._ask_handle(result))

    def _ask_handle(self, result):
        self.ask_btn.config(state="normal")
        command = (result.get("command") or "").strip()
        explanation = (result.get("explanation") or "").strip()
        self.log(f"Suggested: {command}")
        if explanation:
            self.log(f"  {explanation}")
        self.git(command)

    def _ask_done(self, error=""):
        self.ask_btn.config(state="normal")
        if error:
            self.log(f"Error: {error}\n")

    # --------------------------------------------------------------- settings
    def open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Settings")
        win.configure(bg=BG)
        win.geometry("520x420")
        win.transient(self.root)
        win.grab_set()

        pad = {"padx": 14, "pady": 4}
        provider = tk.StringVar(value=("openai" if core.PROVIDER == "openai" else "ollama"))

        ttk.Label(win, text="Provider", background=BG,
                  font=("Helvetica", 11, "bold")).pack(anchor="w", **pad)
        prow = ttk.Frame(win, style="App.TFrame")
        prow.pack(fill="x", padx=14)
        ttk.Radiobutton(prow, text="Ollama (local, offline)", value="ollama",
                        variable=provider).pack(side="left")
        ttk.Radiobutton(prow, text="Bynara / OpenAI-compatible (cloud)", value="openai",
                        variable=provider).pack(side="left", padx=10)

        # --- Bynara / cloud ---
        ttk.Label(win, text="Bynara API key", background=BG,
                  font=("Helvetica", 11, "bold")).pack(anchor="w", **pad)
        krow = ttk.Frame(win, style="App.TFrame")
        krow.pack(fill="x", padx=14)
        key_entry = ttk.Entry(krow, show="•")
        key_entry.insert(0, core.LLM_API_KEY)
        key_entry.pack(side="left", fill="x", expand=True)
        show_var = tk.BooleanVar(value=False)

        def toggle_show():
            key_entry.config(show="" if show_var.get() else "•")
        ttk.Checkbutton(krow, text="show", variable=show_var,
                        command=toggle_show).pack(side="left", padx=6)
        ttk.Button(win, text="Sign up & get a key →",
                   command=lambda: webbrowser.open(core.BYNARA_SIGNUP_URL)).pack(anchor="w", padx=14, pady=(6, 0))

        ttk.Label(win, text="Base URL", background=BG).pack(anchor="w", padx=14, pady=(8, 0))
        base_entry = ttk.Entry(win)
        base_entry.insert(0, core.LLM_BASE_URL or core.BYNARA_BASE_URL)
        base_entry.pack(fill="x", padx=14)

        ttk.Label(win, text="Cloud model", background=BG).pack(anchor="w", padx=14, pady=(8, 0))
        mrow = ttk.Frame(win, style="App.TFrame")
        mrow.pack(fill="x", padx=14)
        model_combo = ttk.Combobox(mrow, values=[core.LLM_MODEL] if core.LLM_MODEL else [])
        model_combo.set(core.LLM_MODEL)
        model_combo.pack(side="left", fill="x", expand=True)

        def refresh_models():
            # use whatever key/base is currently typed
            core.apply_config({"LLM_API_KEY": key_entry.get(), "LLM_BASE_URL": base_entry.get()})
            models = core.list_openai_models()
            if models:
                model_combo["values"] = models
                if model_combo.get() not in models:
                    model_combo.set(models[0])
                self.log(f"Loaded {len(models)} models from the router.")
            else:
                self.log("Could not load models (check the key/base URL).")
        ttk.Button(mrow, text="Refresh", command=refresh_models).pack(side="left", padx=6)

        # --- Ollama ---
        ttk.Label(win, text="Ollama model", background=BG).pack(anchor="w", padx=14, pady=(8, 0))
        ollama_entry = ttk.Entry(win)
        ollama_entry.insert(0, core.OLLAMA_MODEL)
        ollama_entry.pack(fill="x", padx=14)

        def save():
            values = {
                "PROVIDER": provider.get(),
                "LLM_API_KEY": key_entry.get().strip(),
                "LLM_BASE_URL": base_entry.get().strip(),
                "LLM_MODEL": model_combo.get().strip(),
                "OLLAMA_MODEL": ollama_entry.get().strip(),
            }
            try:
                path = core.update_env(values)
            except Exception as e:
                messagebox.showerror("Save failed", str(e))
                return
            self._refresh_badge()
            self.log(f"Settings saved to {path}. Provider: {core.PROVIDER}, model: "
                     f"{core.LLM_MODEL if core.PROVIDER == 'openai' else core.OLLAMA_MODEL}\n")
            win.destroy()

        btns = ttk.Frame(win, style="App.TFrame")
        btns.pack(fill="x", padx=14, pady=14)
        ttk.Button(btns, text="Cancel", command=win.destroy).pack(side="right")
        ttk.Button(btns, text="Save", style="Primary.TButton",
                   command=save).pack(side="right", padx=6)


def main():
    root = tk.Tk()
    GitAIApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
