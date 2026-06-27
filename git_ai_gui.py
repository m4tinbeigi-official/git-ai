#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
git-ai — chat-first graphical interface (Tkinter), modern dark theme.

Talk to git like you'd talk to a person. No git or programming knowledge needed.

  - Projects sidebar: add folders, switch between them, or create a brand-new repo.
  - Conversational chat: type what you want; the assistant explains, runs safe
    git commands automatically, and asks before anything irreversible.
  - Smart commit messages, GitHub login, settings, About — from chat or buttons.

Uses the git_ai core. No keys or tokens live in this code.
"""

import os
import re
import threading
import webbrowser
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import git_ai as core

# --- modern dark palette -------------------------------------------------
BG       = "#0d1117"   # app background
PANEL    = "#161b22"   # header / sidebar / input bar
ELEV     = "#21262d"   # raised elements (bot bubble, chips, buttons)
ELEV2    = "#2d333b"   # hover
BORDER   = "#30363d"
INK      = "#e6edf3"   # primary text (high contrast)
MUTED    = "#8b949e"   # secondary text
ACCENT   = "#388bfd"   # vivid blue
ACCENT_H = "#1f6feb"   # accent hover
VIOLET   = "#a371f7"
OK       = "#3fb950"
DANGER   = "#f85149"
STAR     = "#e3b341"
USER_BG  = "#1f6feb"
USER_FG  = "#ffffff"
BOT_BG   = "#21262d"
BOT_FG   = "#e6edf3"
TERM_BG  = "#010409"
TERM_FG  = "#7ee787"
FONT     = "Helvetica"
MONO     = "Menlo"
WRAP     = 500


class GitAIApp:
    def __init__(self, root):
        self.root = root
        self.repo_path = None
        self.projects = core.load_projects()
        self.pending = None
        self.typing_frame = None

        root.title("git-ai")
        root.geometry("1040x740")
        root.minsize(860, 620)
        root.configure(bg=BG)

        self._init_style()
        self._build_topbar()

        main = tk.Frame(root, bg=BG)
        main.pack(fill="both", expand=True)
        self._build_sidebar(main)
        self._build_chat(main)

        self.render_projects()
        if self.projects:
            self.set_active(self.projects[0], announce=False)

        self.bot("👋 Hi! I'm your git assistant. Tell me what you want — e.g. "
                 "\"commit my changes\", \"create a new project called notes\", or "
                 "\"push to GitHub\". No git knowledge needed.")
        if not self.projects:
            self.bot_actions("First, let's pick a project to work on:",
                             [("📂 Open a folder", self.open_project),
                              ("✨ Create new project", self.new_project_dialog)])
        if core.PROVIDER == "openai" and not core.LLM_API_KEY:
            self.bot_actions("To use the cloud AI, you'll need a free API key. I can walk you "
                             "through it — or set it up now:",
                             [("How does this work?", lambda: self._setup_message(False)),
                              ("Sign up & get a key", lambda: webbrowser.open(core.BYNARA_SIGNUP_URL)),
                              ("Open Settings", self.open_settings)])
        self.refresh_github_status()

    # ------------------------------------------------------------- styling
    def _init_style(self):
        # Use the cross-platform 'clam' theme; avoid custom ttk style options,
        # which some Tk builds (e.g. Tk 9 on macOS) reject at widget creation.
        try:
            ttk.Style().theme_use("clam")
        except tk.TclError:
            pass
        # Style only the combobox dropdown list (plain Tk options — always safe).
        self.root.option_add("*TCombobox*Listbox.background", PANEL)
        self.root.option_add("*TCombobox*Listbox.foreground", INK)
        self.root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#fff")

    def _flatbtn(self, parent, text, cmd, bg=ELEV, fg=INK, hover=ELEV2,
                 font=None, padx=10, pady=5, bold=False):
        b = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg, relief="flat",
                      bd=0, cursor="hand2", activebackground=hover, activeforeground=fg,
                      font=font or (FONT, 10, "bold" if bold else "normal"),
                      padx=padx, pady=pady, highlightthickness=0)
        b.bind("<Enter>", lambda e: b.config(bg=hover))
        b.bind("<Leave>", lambda e: b.config(bg=bg))
        return b

    def _build_topbar(self):
        bar = tk.Frame(self.root, bg=PANEL, height=58)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        # gradient-ish accent strip
        tk.Frame(self.root, bg=ACCENT, height=2).pack(fill="x")

        wrap = tk.Frame(bar, bg=PANEL)
        wrap.pack(side="left", padx=18)
        tk.Label(wrap, text="git", bg=PANEL, fg=INK,
                 font=(FONT, 18, "bold")).pack(side="left")
        tk.Label(wrap, text="-ai", bg=PANEL, fg=ACCENT,
                 font=(FONT, 18, "bold")).pack(side="left")
        tk.Label(bar, text="chat with your repositories", bg=PANEL, fg=MUTED,
                 font=(FONT, 10)).pack(side="left", pady=(4, 0))

        self._flatbtn(bar, "⚙  Settings", self.open_settings, bg=PANEL, hover=ELEV
                      ).pack(side="right", padx=(4, 14))
        self._flatbtn(bar, "ⓘ  About", self.open_about, bg=PANEL, hover=ELEV
                      ).pack(side="right", padx=4)
        self.login_btn = self._flatbtn(bar, "GitHub", self.github_login, bg=PANEL, hover=ELEV)
        self.login_btn.pack(side="right", padx=4)
        self.star_badge = self._flatbtn(bar, "⭐ …", lambda: webbrowser.open(core.LINK_PROJECT),
                                        bg=ELEV, fg=STAR, hover=ELEV2, bold=True)
        self.star_badge.pack(side="right", padx=4)
        self.refresh_stars()

    # ------------------------------------------------------------- sidebar
    def _build_sidebar(self, parent):
        side = tk.Frame(parent, bg=PANEL, width=230)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        tk.Frame(parent, bg=BORDER, width=1).pack(side="left", fill="y")

        tk.Label(side, text="PROJECTS", bg=PANEL, fg=MUTED,
                 font=(FONT, 9, "bold")).pack(anchor="w", padx=16, pady=(16, 8))
        self.proj_list = tk.Frame(side, bg=PANEL)
        self.proj_list.pack(fill="both", expand=True, padx=8)

        btns = tk.Frame(side, bg=PANEL)
        btns.pack(fill="x", padx=12, pady=12)
        self._flatbtn(btns, "📂  Open folder", self.open_project, bg=ELEV, hover=ELEV2,
                      pady=8).pack(fill="x", pady=3)
        self._flatbtn(btns, "✨  New project", self.new_project_dialog, bg=ACCENT,
                      fg="#fff", hover=ACCENT_H, pady=8, bold=True).pack(fill="x", pady=3)

    def render_projects(self):
        for w in self.proj_list.winfo_children():
            w.destroy()
        if not self.projects:
            tk.Label(self.proj_list, text="No projects yet.\nOpen or create one below.",
                     bg=PANEL, fg=MUTED, font=(FONT, 9), wraplength=190,
                     justify="left").pack(anchor="w", padx=8, pady=4)
            return
        for p in self.projects:
            active = (p == self.repo_path)
            bg = ACCENT if active else PANEL
            row = tk.Frame(self.proj_list, bg=bg)
            row.pack(fill="x", pady=2)
            name = os.path.basename(p.rstrip("/")) or p
            fg = "#fff" if active else INK
            lbl = tk.Label(row, text=("●  " if active else "○  ") + name, bg=bg, fg=fg,
                           font=(FONT, 10, "bold" if active else "normal"),
                           anchor="w", cursor="hand2", padx=10, pady=8)
            lbl.pack(side="left", fill="x", expand=True)
            lbl.bind("<Button-1>", lambda e, path=p: self.set_active(path))
            x = tk.Label(row, text="✕", bg=bg, fg=("#fff" if active else MUTED),
                         cursor="hand2", padx=8)
            x.pack(side="right")
            x.bind("<Button-1>", lambda e, path=p: self.remove_project(path))
            if not active:
                for w in (row, lbl):
                    w.bind("<Enter>", lambda e, r=row, l=lbl, xx=x: (r.config(bg=ELEV), l.config(bg=ELEV), xx.config(bg=ELEV)))
                    w.bind("<Leave>", lambda e, r=row, l=lbl, xx=x: (r.config(bg=PANEL), l.config(bg=PANEL), xx.config(bg=PANEL)))

    def open_project(self):
        path = filedialog.askdirectory(title="Open a project folder")
        if not path:
            return
        self.projects = core.add_project(path)
        self.set_active(path)

    def remove_project(self, path):
        self.projects = core.remove_project(path)
        if self.repo_path == path:
            self.repo_path = None
            self.update_active_header()
        self.render_projects()
        self.bot(f"Removed “{os.path.basename(path)}” from the list (the folder is untouched).")

    def set_active(self, path, announce=True):
        self.repo_path = path
        self.render_projects()
        self.update_active_header()
        if announce:
            branch = core.get_branch(path)
            if not os.path.isdir(os.path.join(path, ".git")):
                self.bot_actions(f"Switched to “{os.path.basename(path)}”. This folder isn't a "
                                 "git repo yet — want me to set it up?",
                                 [("Yes, initialize git", lambda: self.run_git("git init"))])
            else:
                self.bot(f"Switched to “{os.path.basename(path)}” (branch: {branch or 'none yet'}).")

    def new_project_dialog(self):
        self.pending = {"type": "new_repo_name"}
        self.bot("Sure! What should the new project be called?")

    # --------------------------------------------------------------- chat
    def _build_chat(self, parent):
        wrap = tk.Frame(parent, bg=BG)
        wrap.pack(side="left", fill="both", expand=True)

        self.active_header = tk.Label(wrap, text="No project selected", bg=PANEL,
                                      fg=MUTED, anchor="w", font=(FONT, 10),
                                      padx=16, pady=8)
        self.active_header.pack(fill="x")
        tk.Frame(wrap, bg=BORDER, height=1).pack(fill="x")

        cwrap = tk.Frame(wrap, bg=BG)
        cwrap.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(cwrap, bg=BG, highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(cwrap, orient="vertical", command=self.canvas.yview)
        sb.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=sb.set)
        self.msgs = tk.Frame(self.canvas, bg=BG)
        self.win = self.canvas.create_window((0, 0), window=self.msgs, anchor="nw")
        self.msgs.bind("<Configure>",
                       lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.win, width=e.width))
        self._bind_scroll()

        # toolbar
        tb = tk.Frame(wrap, bg=BG)
        tb.pack(fill="x", padx=14, pady=(6, 0))
        for text, cmd in [("Status", lambda: self.run_git("git status")),
                          ("Commit", self.smart_commit),
                          ("Pull", lambda: self.run_git("git pull")),
                          ("Push", self.do_push),
                          ("↩ Undo last", self.undo_last)]:
            self._flatbtn(tb, text, cmd, bg=ELEV, hover=ELEV2, font=(FONT, 9),
                          padx=10, pady=5).pack(side="left", padx=3)

        # suggestion chips
        chips = tk.Frame(wrap, bg=BG)
        chips.pack(fill="x", padx=14, pady=(8, 2))
        tk.Label(chips, text="Try:", bg=BG, fg=MUTED, font=(FONT, 9)).pack(side="left", padx=(0, 6))
        for text in ["What changed?", "Commit my changes", "Push to GitHub",
                     "Create a new project", "Undo my last commit"]:
            self._flatbtn(chips, text, lambda t=text: self.suggest(t), bg=ELEV,
                          fg="#79c0ff", hover=ELEV2, font=(FONT, 9), padx=10, pady=4
                          ).pack(side="left", padx=3)

        # input row
        row = tk.Frame(wrap, bg=BG)
        row.pack(fill="x", padx=14, pady=12)
        field = tk.Frame(row, bg=ELEV, highlightbackground=BORDER, highlightthickness=1)
        field.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry = tk.Entry(field, font=(FONT, 12), bg=ELEV, fg=INK, relief="flat",
                              insertbackground=INK, disabledbackground=ELEV)
        self.entry.pack(fill="x", padx=10, ipady=9)
        self.entry.bind("<Return>", lambda e: self.on_send())
        self.entry.bind("<FocusIn>", lambda e: field.config(highlightbackground=ACCENT, highlightcolor=ACCENT))
        self.entry.bind("<FocusOut>", lambda e: field.config(highlightbackground=BORDER, highlightcolor=BORDER))
        self.entry.focus_set()
        self.send_btn = self._flatbtn(row, "Send  ➤", self.on_send, bg=ACCENT, fg="#fff",
                                      hover=ACCENT_H, font=(FONT, 11, "bold"),
                                      padx=18, pady=9)
        self.send_btn.pack(side="right")

    def _bind_scroll(self):
        def on_wheel(e):
            delta = -1 * (e.delta // 120) if e.delta else (1 if e.num == 5 else -1)
            self.canvas.yview_scroll(delta, "units")
        self.canvas.bind_all("<MouseWheel>", on_wheel)
        self.canvas.bind_all("<Button-4>", on_wheel)
        self.canvas.bind_all("<Button-5>", on_wheel)

    def _scroll_bottom(self):
        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.yview_moveto(1.0)

    def update_active_header(self):
        if self.repo_path:
            b = core.get_branch(self.repo_path)
            self.active_header.config(
                text=f"  📁 {os.path.basename(self.repo_path)}     ⎇ {b or 'no branch yet'}",
                fg=INK)
        else:
            self.active_header.config(text="No project selected", fg=MUTED)

    # --- bubbles (design-system message renderer) ---
    def _bubble(self, text, side, bg, fg, sender=None, name_fg=MUTED, mono=False):
        anchor = "e" if side == "right" else "w"
        row = tk.Frame(self.msgs, bg=BG)
        row.pack(fill="x", padx=18, pady=(8, 2))
        col = tk.Frame(row, bg=BG)
        col.pack(side=side)
        if sender:
            head = tk.Frame(col, bg=BG)
            head.pack(anchor=anchor, padx=6, pady=(0, 3))
            if side == "left":
                tk.Label(head, text="✦", bg=BG, fg=ACCENT, font=(FONT, 9)).pack(side="left", padx=(0, 4))
            tk.Label(head, text=sender, bg=BG, fg=name_fg,
                     font=(FONT, 8, "bold")).pack(side="left")
        font = (MONO, 10) if mono else (FONT, 11)
        lbl = tk.Label(col, text=text, bg=bg, fg=fg, font=font, wraplength=WRAP,
                       justify="left", anchor="w", padx=15, pady=11)
        lbl.pack(anchor=anchor)
        self._scroll_bottom()
        return row

    def user(self, text):
        self._bubble(text, "right", USER_BG, USER_FG, sender="YOU", name_fg=MUTED)

    def bot(self, text):
        self._bubble(text, "left", BOT_BG, BOT_FG, sender="git-ai", name_fg="#79c0ff")

    def term(self, text):
        self._bubble(text, "left", TERM_BG, TERM_FG, sender="git-ai · output",
                     name_fg=MUTED, mono=True)

    def bot_actions(self, text, buttons):
        row = tk.Frame(self.msgs, bg=BG)
        row.pack(fill="x", padx=18, pady=(8, 2))
        col = tk.Frame(row, bg=BG)
        col.pack(side="left")
        head = tk.Frame(col, bg=BG)
        head.pack(anchor="w", padx=6, pady=(0, 3))
        tk.Label(head, text="✦", bg=BG, fg=ACCENT, font=(FONT, 9)).pack(side="left", padx=(0, 4))
        tk.Label(head, text="git-ai", bg=BG, fg="#79c0ff",
                 font=(FONT, 8, "bold")).pack(side="left")
        box = tk.Frame(col, bg=BOT_BG)
        box.pack(anchor="w")
        tk.Label(box, text=text, bg=BOT_BG, fg=BOT_FG, font=(FONT, 11),
                 wraplength=WRAP, justify="left", anchor="w", padx=15, pady=11).pack(anchor="w")
        brow = tk.Frame(box, bg=BOT_BG)
        brow.pack(anchor="w", padx=12, pady=(0, 12))
        for label, cb in buttons:
            self._flatbtn(brow, label, lambda c=cb, r=row: self._click_action(c, r),
                          bg=ACCENT, fg="#fff", hover=ACCENT_H, font=(FONT, 10),
                          padx=12, pady=6).pack(side="left", padx=4)
        self._scroll_bottom()

    def _click_action(self, cb, row):
        for w in row.winfo_children():
            for sub in w.winfo_children():
                if isinstance(sub, tk.Frame):
                    for b in sub.winfo_children():
                        try:
                            b.configure(state="disabled")
                        except tk.TclError:
                            pass
        cb()

    def _typing_on(self):
        self.typing_frame = self._bubble("● ● ●", "left", BOT_BG, MUTED)

    def _typing_off(self):
        if self.typing_frame:
            self.typing_frame.destroy()
            self.typing_frame = None

    # ------------------------------------------------------------- sending
    def on_send(self):
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, "end")
        self.user(text)
        if self.pending:
            self._resolve_pending(text)
            return
        intent = core.detect_intent(text)
        if intent == "new_repo":
            self._start_new_repo(text)
        elif intent == "switch_project":
            self._switch_by_text(text)
        elif self._local_reply(text):
            return
        else:
            self._chat_assistant(text)

    _GREET_RE = re.compile(r"^\s*(hi|hello|hey|hiya|yo|howdy|salam|salaam|سلام|درود)\b", re.IGNORECASE)
    _HELP_RE = re.compile(
        r"(what can you do|what do you do|what(?:'s| is) this|who are you|how (?:do|does) (?:you|this)|"
        r"\bhelp\b|چیکار|چی\s?کار|چه\s?کار|کمک|راهنما|چیه|چی\s?هست|قابلیت)", re.IGNORECASE)
    _AUTHOR_RE = re.compile(
        r"(who (?:made|wrote|created|built|develop|design)|who(?:'s| is)\s+(?:behind|the (?:author|creator|developer|dev))|"
        r"\bauthor\b|\bcreator\b|سازنده|سازندش|نویسنده|کی (?:نوشت|ساخت|درست)|چه کسی|توسعه\s?دهنده)",
        re.IGNORECASE)
    _SETUP_RE = re.compile(
        r"(how (?:do|can) i (?:use|start|set ?up|setup|run)|get(?:ting)? started|set ?up\b|setup|"
        r"sign ?up|register|api ?key|web ?service|automatic(?:ally)?|چطور(?:ی)?\s?(?:استفاده|راه|کار)|"
        r"راه\s?انداز|ثبت\s?نام|کلید|وب\s?سرویس|خودکار|ای\s?پی\s?ای|اکانت)", re.IGNORECASE)

    @staticmethod
    def _lang(text):
        return "fa" if re.search(r"[؀-ۿ]", text or "") else "en"

    def _local_reply(self, text):
        """Answer greetings, capability, author, and setup questions instantly
        (works offline) in the user's language. Returns True if handled."""
        fa = self._lang(text) == "fa"

        if self._AUTHOR_RE.search(text):
            self._author_message(fa)
            return True
        if self._SETUP_RE.search(text):
            self._setup_message(fa)
            return True
        if self._GREET_RE.search(text):
            self.bot("👋 سلام! من git-ai هستم. بگو با مخزنت چی‌کار کنم — کامیت، پوش، پول، "
                     "ساخت شاخه، پروژهٔ جدید یا برگشت یک تغییر. چی لازم داری؟" if fa else
                     "👋 Hey! I'm git-ai. Tell me what you'd like to do with your repository — "
                     "commit, push, pull, create a branch, start a new project, or undo a change.")
            return True
        if self._HELP_RE.search(text):
            self.bot("من زبان طبیعی را به دستورهای گیت تبدیل می‌کنم. می‌تونی بخوای:\n"
                     "• ببینم چی تغییر کرده  • کامیت کنم (پیامش رو خودم می‌نویسم)\n"
                     "• پوش/پول  • پروژه بسازم یا سویچ کنم\n"
                     "• آخرین کامیت رو برگردونم  • وارد گیت‌هاب بشم\n\n"
                     "سوال‌های نامرتبط کار من نیست — فقط گیت و گیت‌هاب. یکی از دکمه‌های پایین رو بزن "
                     "یا هرچی می‌خوای تایپ کن." if fa else
                     "I turn plain language into git actions. You can ask me to:\n"
                     "• see what changed  • commit (I'll write the message)\n"
                     "• push / pull  • create or switch projects\n"
                     "• undo your last commit  • log in to GitHub\n\n"
                     "Off-topic questions aren't my thing — I stick to git & GitHub. "
                     "Try a chip below or just type what you need.")
            return True
        return False

    def _author_message(self, fa):
        if fa:
            self.bot("این پروژه را «ریک سانچز» (یک وایب‌کدر 😎) ساخته. شبکه‌های اجتماعی و پروژه:\n"
                     f"• پروژه: {core.LINK_PROJECT}\n"
                     f"• گیت‌هاب: {core.LINK_GITHUB}\n"
                     f"• توییتر/ایکس: {core.LINK_TWITTER}  (@m4tinbeigi)\n"
                     f"• اینستاگرام: {core.LINK_INSTAGRAM}  (@m4tinbeigi)\n"
                     f"• لینکدین: {core.LINK_LINKEDIN}")
        else:
            self.bot("This project was created by Rick Sanchez (a vibe coder 😎). Links:\n"
                     f"• Project: {core.LINK_PROJECT}\n"
                     f"• GitHub: {core.LINK_GITHUB}\n"
                     f"• Twitter/X: {core.LINK_TWITTER}  (@m4tinbeigi)\n"
                     f"• Instagram: {core.LINK_INSTAGRAM}  (@m4tinbeigi)\n"
                     f"• LinkedIn: {core.LINK_LINKEDIN}")
        self.bot_actions("بیشتر:" if fa else "More:",
                         [("⭐ Star" if not fa else "⭐ ستاره بده", lambda: webbrowser.open(core.LINK_PROJECT)),
                          ("About", self.open_about)])

    def _setup_message(self, fa):
        has_key = bool(core.LLM_API_KEY)
        if fa:
            msg = ("برای استفادهٔ خودکار از هوش مصنوعی ابری، این مراحل رو برو:\n"
                   "۱) از بالا-راست «⚙ Settings» رو باز کن.\n"
                   f"۲) روی «Sign up & get a key →» بزن یا برو به: {core.BYNARA_SIGNUP_URL}\n"
                   "   یک حساب رایگان بساز (ثبت‌نام).\n"
                   "۳) کلید (API key) رو از داشبورد کپی کن.\n"
                   "۴) برگرد توی Settings، کلید رو در فیلد «Bynara API key» بذار، حالت "
                   "«Bynara / OpenAI-compatible» رو انتخاب کن، در صورت دلخواه یک مدل انتخاب کن و Save بزن.\n\n"
                   "بعدش کافیه به فارسی بگی چی می‌خوای؛ من خودکار به دستور گیت تبدیل و اجرا می‌کنم.\n"
                   "🔒 ترجیح می‌دی کاملاً آفلاین باشه؟ Ollama رو نصب کن و در Settings حالت Ollama رو انتخاب کن.")
            if not has_key:
                msg = "⚠️ هنوز کلیدی وارد نکردی، پس هوش مصنوعی ابری فعال نیست.\n\n" + msg
        else:
            msg = ("To use the cloud AI automatically, follow these steps:\n"
                   "1) Open “⚙ Settings” (top-right).\n"
                   f"2) Click “Sign up & get a key →” or visit: {core.BYNARA_SIGNUP_URL}\n"
                   "   Create a free account (register).\n"
                   "3) Copy your API key from the dashboard.\n"
                   "4) Back in Settings, paste it into the “Bynara API key” field, choose the "
                   "“Bynara / OpenAI-compatible” provider, optionally pick a model, and click Save.\n\n"
                   "After that, just tell me what you want in plain language and I'll run git for you.\n"
                   "🔒 Prefer fully offline? Install Ollama and choose the Ollama provider in Settings.")
            if not has_key:
                msg = "⚠️ You haven't entered a key yet, so the cloud AI isn't active.\n\n" + msg
        self.bot(msg)
        self.bot_actions("میانبر:" if fa else "Shortcuts:",
                         [("ثبت‌نام و دریافت کلید" if fa else "Sign up & get a key",
                           lambda: webbrowser.open(core.BYNARA_SIGNUP_URL)),
                          ("باز کردن تنظیمات" if fa else "Open Settings", self.open_settings)])

    def _resolve_pending(self, text):
        kind = self.pending.get("type")
        if kind == "new_repo_name":
            self.pending = None
            self._create_repo_with_name(text)
        elif kind == "confirm":
            cmd = self.pending.get("command")
            self.pending = None
            if text.lower() in ("y", "yes", "yeah", "ok", "okay", "بله", "اره", "آره"):
                self.run_git(cmd, dangerous_ok=True)
            else:
                self.bot("Okay, I won't run it.")
        else:
            self.pending = None

    def _start_new_repo(self, text):
        m = re.search(r"(?:called|named|name|به ?نام|اسم(?:ش)?)\s+['\"]?([\w.\- ]{1,40})",
                      text, re.IGNORECASE)
        if m:
            self._create_repo_with_name(m.group(1).strip())
        else:
            self.pending = {"type": "new_repo_name"}
            self.bot("What should the new project be called?")

    def _create_repo_with_name(self, name):
        parent = filedialog.askdirectory(title="Where should the new project live?")
        if not parent:
            self.bot("No location chosen, so I didn't create it. Try again anytime.")
            return
        path, out = core.create_local_repo(parent, name)
        self.projects = core.add_project(path)
        self.set_active(path, announce=False)
        self.bot(f"✅ Created “{os.path.basename(path)}” and initialized git.")
        self.term(out)
        self.bot_actions("Want me to make the first commit?",
                         [("Yes, first commit", self._first_commit)])

    def _first_commit(self):
        self.run_git("git add -A", silent=True)
        self.run_git('git commit -m "Initial commit"')

    def _switch_by_text(self, text):
        match = None
        for p in self.projects:
            if os.path.basename(p).lower() in text.lower():
                match = p
                break
        if match:
            self.set_active(match)
        elif self.projects:
            self.bot_actions("Which project?",
                             [(os.path.basename(p), lambda path=p: self.set_active(path))
                              for p in self.projects])
        else:
            self.bot_actions("You don't have any projects yet.",
                             [("📂 Open a folder", self.open_project),
                              ("✨ Create new project", self.new_project_dialog)])

    def _chat_assistant(self, text):
        self._typing_on()
        self.send_btn.config(state="disabled")
        threading.Thread(target=self._assistant_worker, args=(text,), daemon=True).start()

    def _assistant_worker(self, text):
        try:
            result = core.assistant_reply(text, cwd=self.repo_path)
        except Exception as e:
            self.root.after(0, lambda: self._assistant_error(str(e)))
            return
        self.root.after(0, lambda: self._assistant_done(result))

    def _assistant_error(self, msg):
        self._typing_off()
        self.send_btn.config(state="normal")
        self.bot(f"⚠️ I couldn't reach the model: {msg}\n\nCheck Settings (provider/key), "
                 "or make sure Ollama is running.")

    def _assistant_done(self, result):
        self._typing_off()
        self.send_btn.config(state="normal")
        kind_t = result.get("type", "talk")
        reply = result.get("reply", "")
        command = result.get("command", "")

        # conversational or out-of-scope
        if kind_t in ("talk", "reject"):
            self.bot(reply or "I'm here to help with git and GitHub.")
            return

        # git action
        if reply:
            self.bot(reply)
        if not self.repo_path:
            self.bot_actions("First, pick a project so I can run that:",
                             [("📂 Open a folder", self.open_project),
                              ("✨ Create new project", self.new_project_dialog)])
            return
        kind, msg = core.classify_command(command)
        if kind == "invalid":
            self.bot("I couldn't form a safe git command for that. Could you rephrase? "
                     "For example: \"show what changed\" or \"commit everything\".")
            return
        if kind == "blocked":
            self.bot(f"🚫 I won't run that — it looks unsafe.\n{command}")
            return
        if kind == "dangerous":
            self.pending = {"type": "confirm", "command": command}
            self.bot_actions(f"This is irreversible:\n{command}\nRun it?",
                             [("Run it", lambda: self.run_git(command, dangerous_ok=True)),
                              ("Cancel", lambda: self.bot("Okay, cancelled."))])
            return
        self.run_git(command)

    # ------------------------------------------------------- run + helpers
    def run_git(self, command, dangerous_ok=False, silent=False):
        if not self.repo_path:
            self.bot("Open a project first.")
            return
        kind, msg = core.classify_command(command)
        if kind in ("invalid", "blocked"):
            self.bot(f"Not run: {msg}")
            return
        if kind == "dangerous" and not dangerous_ok:
            self.bot_actions(f"This is irreversible:\n{command}\nRun it?",
                             [("Run it", lambda: self.run_git(command, dangerous_ok=True)),
                              ("Cancel", lambda: self.bot("Okay, cancelled."))])
            return
        out = core.run_command_capture(command, cwd=self.repo_path)
        if not silent:
            self.term(f"$ {command}\n{out}")
        self.update_active_header()
        self.render_projects()

    def do_push(self):
        if not self.repo_path:
            self.bot("Open a project first.")
            return
        branch = core.get_branch(self.repo_path) or "HEAD"
        self.run_git(f"git push -u origin {branch}")

    def suggest(self, text):
        self.entry.delete(0, "end")
        self.entry.insert(0, text)
        self.on_send()

    def undo_last(self):
        if not self.repo_path:
            self.bot("Open a project first.")
            return
        last = core.run_git_context_cmd(["git", "log", "--oneline", "-1"], self.repo_path)
        self.bot_actions(
            f"I'll undo your last commit safely with a new \"revert\" commit "
            f"(nothing is lost; you can redo it).\n\nLast commit: {last or '(none)'}",
            [("↩ Undo it", lambda: self.run_git("git revert HEAD --no-edit")),
             ("Cancel", lambda: self.bot("Okay, left as is."))])

    def smart_commit(self):
        if not self.repo_path:
            self.bot("Open a project first.")
            return
        self.bot("Looking at your changes to write a commit message…")
        self._typing_on()
        threading.Thread(target=self._smart_commit_worker, daemon=True).start()

    def _smart_commit_worker(self):
        try:
            msg = core.generate_commit_message(cwd=self.repo_path)
        except Exception as e:
            self.root.after(0, lambda: (self._typing_off(), self.bot(f"⚠️ {e}")))
            return
        self.root.after(0, lambda: self._smart_commit_done(msg))

    def _smart_commit_done(self, msg):
        self._typing_off()
        title = msg.get("title", "")
        desc = msg.get("description", "")
        preview = title + (f"\n\n{desc}" if desc else "")
        cmd = f'git add -A && git commit -m "{title.replace(chr(34), chr(92)+chr(34))}"'
        if desc:
            cmd += f' -m "{desc.replace(chr(34), chr(92)+chr(34))}"'
        self.bot_actions(f"Here's a commit message I drafted:\n\n{preview}",
                         [("✅ Commit it", lambda: self.run_git(cmd)),
                          ("🚀 Commit & push", lambda: (self.run_git(cmd), self.do_push()))])

    # ----------------------------------------------------------- GitHub gh
    def refresh_github_status(self):
        threading.Thread(target=self._gh_status_worker, daemon=True).start()

    def _gh_status_worker(self):
        acct = core.gh_account() if core.gh_available() else None
        def update():
            self.login_btn.config(text=(f"GitHub: {acct}" if acct else "GitHub: Login"),
                                  fg=(OK if acct else INK))
        self.root.after(0, update)

    def github_login(self):
        if not core.gh_available():
            self.bot("To use GitHub I need the GitHub CLI (gh). Install it from cli.github.com, "
                     "then click GitHub again.")
            return
        if core.gh_account():
            self.bot(f"You're already signed in to GitHub as {core.gh_account()}.")
            return
        self.bot("Starting GitHub login — I'll show you a code to enter in your browser…")
        threading.Thread(target=self._gh_login_worker, daemon=True).start()

    def _gh_login_worker(self):
        try:
            proc = subprocess.Popen(
                ["gh", "auth", "login", "--web", "--git-protocol", "https", "--hostname", "github.com"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            )
            try:
                proc.stdin.write("\n")
                proc.stdin.flush()
            except Exception:
                pass
            code = None
            for line in iter(proc.stdout.readline, ""):
                m = re.search(r"one-time code:?\s*([A-Z0-9-]{6,})", line.strip())
                if m and not code:
                    code = m.group(1)
                    self.root.after(0, lambda c=code: self._show_code(c))
            proc.wait(timeout=300)
        except Exception as e:
            self.root.after(0, lambda: self.bot(f"Login error: {e}"))
        finally:
            self.root.after(0, self.refresh_github_status)

    def _show_code(self, code):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(code)
        except Exception:
            pass
        webbrowser.open("https://github.com/login/device")
        self.bot(f"🔑 Your one-time code is {code} (copied to clipboard). Enter it in the "
                 "browser window that just opened, then approve.")

    # --------------------------------------------------------------- about
    def refresh_stars(self):
        threading.Thread(target=self._stars_worker, daemon=True).start()

    def _stars_worker(self):
        n = core.get_repo_stars()
        text = f"⭐ {n}" if n is not None else "⭐ Star"
        self.root.after(0, lambda: self.star_badge.config(text=text))

    def open_about(self):
        win = tk.Toplevel(self.root)
        win.title("About git-ai")
        win.configure(bg=BG)
        win.geometry("480x560")
        win.transient(self.root)
        win.grab_set()
        tk.Frame(win, bg=ACCENT, height=3).pack(fill="x")

        tk.Label(win, text="git-ai", bg=BG, fg=INK, font=(FONT, 26, "bold")).pack(pady=(26, 0))
        tk.Label(win, text="An AI-powered git assistant", bg=BG, fg=MUTED,
                 font=(FONT, 11)).pack()

        star_lbl = tk.Label(win, text="⭐ … stars", bg=BG, fg=STAR, font=(FONT, 15, "bold"))
        star_lbl.pack(pady=(18, 6))
        threading.Thread(
            target=lambda: self.root.after(
                0, lambda n=core.get_repo_stars():
                star_lbl.config(text=(f"⭐ {n} stars on GitHub" if n is not None
                                      else "⭐ Star us on GitHub"))),
            daemon=True).start()

        self._flatbtn(win, "⭐  Star this project on GitHub",
                      lambda: webbrowser.open(core.LINK_PROJECT), bg=ACCENT, fg="#fff",
                      hover=ACCENT_H, font=(FONT, 11, "bold"), padx=16, pady=8).pack(pady=(4, 8))
        tk.Label(win, text="If git-ai helps you, a star means a lot 💛", bg=BG, fg=MUTED,
                 font=(FONT, 10)).pack()

        tk.Frame(win, bg=BORDER, height=1).pack(fill="x", padx=40, pady=20)
        tk.Label(win, text="Created by", bg=BG, fg=MUTED, font=(FONT, 10)).pack()
        tk.Label(win, text=core.AUTHOR_NAME, bg=BG, fg=INK,
                 font=(FONT, 17, "bold")).pack()
        tk.Label(win, text=core.AUTHOR_TAGLINE, bg=BG, fg=VIOLET,
                 font=(FONT, 11, "italic")).pack(pady=(0, 12))

        for text, url in [
            ("🔗  Project repository", core.LINK_PROJECT),
            ("🐙  GitHub", core.LINK_GITHUB),
            ("🐦  Twitter / X — @m4tinbeigi", core.LINK_TWITTER),
            ("📸  Instagram — @m4tinbeigi", core.LINK_INSTAGRAM),
            ("💼  LinkedIn", core.LINK_LINKEDIN),
        ]:
            lk = tk.Label(win, text=text, bg=BG, fg="#79c0ff", cursor="hand2",
                          font=(FONT, 11, "underline"))
            lk.pack(pady=3)
            lk.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))

        self._flatbtn(win, "Close", win.destroy, bg=ELEV, hover=ELEV2,
                      padx=16, pady=6).pack(pady=20)

    # --------------------------------------------------------------- settings
    def open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Settings")
        win.configure(bg=PANEL)
        win.geometry("540x470")
        win.transient(self.root)
        win.grab_set()
        tk.Frame(win, bg=ACCENT, height=3).pack(fill="x")
        body = tk.Frame(win, bg=PANEL)
        body.pack(fill="both", expand=True, padx=16, pady=10)

        provider = tk.StringVar(value=("openai" if core.PROVIDER == "openai" else "ollama"))
        tk.Label(body, text="Provider", bg=PANEL, fg=INK,
                 font=(FONT, 11, "bold")).pack(anchor="w", pady=(4, 2))
        prow = tk.Frame(body, bg=PANEL)
        prow.pack(fill="x")
        tk.Radiobutton(prow, text="Ollama (local, offline)", value="ollama",
                       variable=provider, bg=PANEL, fg=INK, selectcolor=BG,
                       activebackground=PANEL, activeforeground=INK,
                       highlightthickness=0, font=(FONT, 10)).pack(side="left")
        tk.Radiobutton(prow, text="Bynara / OpenAI-compatible (cloud)", value="openai",
                       variable=provider, bg=PANEL, fg=INK, selectcolor=BG,
                       activebackground=PANEL, activeforeground=INK,
                       highlightthickness=0, font=(FONT, 10)).pack(side="left", padx=10)

        tk.Label(body, text="Bynara API key", bg=PANEL, fg=INK,
                 font=(FONT, 11, "bold")).pack(anchor="w", pady=(12, 2))
        krow = tk.Frame(body, bg=PANEL)
        krow.pack(fill="x")
        key_entry = tk.Entry(krow, show="•", bg=BG, fg=INK, insertbackground=INK,
                             relief="flat", font=(FONT, 11))
        key_entry.insert(0, core.LLM_API_KEY)
        key_entry.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 6))
        show = tk.BooleanVar(value=False)
        tk.Checkbutton(krow, text="show", variable=show, bg=PANEL, fg=INK,
                       selectcolor=BG, activebackground=PANEL, activeforeground=INK,
                       highlightthickness=0, font=(FONT, 10),
                       command=lambda: key_entry.config(show="" if show.get() else "•")
                       ).pack(side="left")
        self._flatbtn(body, "Sign up & get a key →",
                      lambda: webbrowser.open(core.BYNARA_SIGNUP_URL), bg=ELEV, fg="#79c0ff",
                      hover=ELEV2, padx=10, pady=5).pack(anchor="w", pady=(8, 0))

        tk.Label(body, text="Base URL", bg=PANEL, fg=MUTED, font=(FONT, 10)).pack(anchor="w", pady=(10, 2))
        base_entry = tk.Entry(body, bg=BG, fg=INK, insertbackground=INK, relief="flat", font=(FONT, 11))
        base_entry.insert(0, core.LLM_BASE_URL or core.BYNARA_BASE_URL)
        base_entry.pack(fill="x", ipady=5)

        tk.Label(body, text="Cloud model", bg=PANEL, fg=MUTED, font=(FONT, 10)).pack(anchor="w", pady=(10, 2))
        mrow = tk.Frame(body, bg=PANEL)
        mrow.pack(fill="x")
        model_combo = ttk.Combobox(mrow, values=[core.LLM_MODEL] if core.LLM_MODEL else [])
        model_combo.set(core.LLM_MODEL)
        model_combo.pack(side="left", fill="x", expand=True, ipady=2)

        def refresh_models():
            core.apply_config({"LLM_API_KEY": key_entry.get(), "LLM_BASE_URL": base_entry.get()})
            models = core.list_openai_models()
            if models:
                model_combo["values"] = models
                if model_combo.get() not in models:
                    model_combo.set(models[0])
        self._flatbtn(mrow, "Refresh", refresh_models, bg=ELEV, hover=ELEV2,
                      padx=10, pady=4).pack(side="left", padx=6)

        tk.Label(body, text="Ollama model", bg=PANEL, fg=MUTED, font=(FONT, 10)).pack(anchor="w", pady=(10, 2))
        ollama_entry = tk.Entry(body, bg=BG, fg=INK, insertbackground=INK, relief="flat", font=(FONT, 11))
        ollama_entry.insert(0, core.OLLAMA_MODEL)
        ollama_entry.pack(fill="x", ipady=5)

        def save():
            try:
                core.update_env({
                    "PROVIDER": provider.get(),
                    "LLM_API_KEY": key_entry.get().strip(),
                    "LLM_BASE_URL": base_entry.get().strip(),
                    "LLM_MODEL": model_combo.get().strip(),
                    "OLLAMA_MODEL": ollama_entry.get().strip(),
                })
            except Exception as e:
                messagebox.showerror("Save failed", str(e))
                return
            self.bot(f"Settings saved. Using {core.PROVIDER} · "
                     f"{core.LLM_MODEL if core.PROVIDER == 'openai' else core.OLLAMA_MODEL}.")
            win.destroy()

        btns = tk.Frame(body, bg=PANEL)
        btns.pack(fill="x", pady=16)
        self._flatbtn(btns, "Save", save, bg=ACCENT, fg="#fff", hover=ACCENT_H,
                      font=(FONT, 11, "bold"), padx=16, pady=6).pack(side="right")
        self._flatbtn(btns, "Cancel", win.destroy, bg=ELEV, hover=ELEV2,
                      padx=16, pady=6).pack(side="right", padx=8)


def main():
    root = tk.Tk()
    GitAIApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
