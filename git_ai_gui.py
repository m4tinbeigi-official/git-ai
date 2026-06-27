#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
git-ai — chat-first graphical interface (Tkinter).

- Multi-language UI (English, Persian, Arabic, French, Spanish) with a switcher.
- Persian & Arabic are right-to-left.
- Vazirmatn font for Persian/Arabic; a clean sans for Latin.
- Talk to git in plain language; safe commands run automatically, risky ones ask.
- Beginner-friendly: publish to GitHub, suggest push after commit, plain-language
  explanation of what each command did.
- Submit feature requests as GitHub issues. No keys/tokens live in this code.
"""

import os
import re
import locale
import ctypes
import platform
import threading
import webbrowser
import subprocess
import urllib.request
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import tkinter.font as tkfont

import git_ai as core
import i18n
from i18n import t

NOQTE_URL = "https://noqte.pro"
HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_history.json")

# --- modern dark palette -------------------------------------------------
BG, PANEL, ELEV, ELEV2, BORDER = "#0d1117", "#161b22", "#21262d", "#2d333b", "#30363d"
INK, MUTED = "#e6edf3", "#8b949e"
ACCENT, ACCENT_H, VIOLET = "#388bfd", "#1f6feb", "#a371f7"
OK, DANGER, STAR = "#3fb950", "#f85149", "#e3b341"
USER_BG, USER_FG, BOT_BG, BOT_FG = "#1f6feb", "#ffffff", "#21262d", "#e6edf3"
TERM_BG, TERM_FG = "#010409", "#7ee787"
FONT = FONT_FA = FONT_EN = "Helvetica"
MONO = "Menlo"
WRAP = 500


# ---------------------------------------------------------------------------
# Fonts (Vazirmatn auto-download + register; graceful fallback)
# ---------------------------------------------------------------------------
_VAZIR_FILES = {
    "Vazirmatn-Regular.ttf": "https://cdn.jsdelivr.net/npm/vazirmatn@33.0.3/fonts/ttf/Vazirmatn-Regular.ttf",
    "Vazirmatn-Bold.ttf":    "https://cdn.jsdelivr.net/npm/vazirmatn@33.0.3/fonts/ttf/Vazirmatn-Bold.ttf",
}


def _font_dir():
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts")
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        pass
    return d


def _register_font_file(path):
    try:
        sysname = platform.system()
        if sysname == "Windows":
            ctypes.windll.gdi32.AddFontResourceExW(ctypes.c_wchar_p(path), 0x10, 0)
            return True
        if sysname == "Darwin":
            from ctypes import util, cdll, c_void_p, c_int, c_char_p
            ct = cdll.LoadLibrary(util.find_library("CoreText"))
            cf = cdll.LoadLibrary(util.find_library("CoreFoundation"))
            cf.CFStringCreateWithCString.restype = c_void_p
            cf.CFStringCreateWithCString.argtypes = [c_void_p, c_char_p, c_int]
            s = cf.CFStringCreateWithCString(None, path.encode("utf-8"), 0x08000100)
            cf.CFURLCreateWithFileSystemPath.restype = c_void_p
            cf.CFURLCreateWithFileSystemPath.argtypes = [c_void_p, c_void_p, c_int, c_int]
            url = cf.CFURLCreateWithFileSystemPath(None, s, 0, False)
            ct.CTFontManagerRegisterFontsForURL.restype = ctypes.c_bool
            ct.CTFontManagerRegisterFontsForURL.argtypes = [c_void_p, c_int, c_void_p]
            return bool(ct.CTFontManagerRegisterFontsForURL(url, 1, None))
        import shutil
        dest = os.path.expanduser("~/.fonts")
        os.makedirs(dest, exist_ok=True)
        shutil.copy(path, dest)
        try:
            subprocess.run(["fc-cache", "-f", dest], timeout=20)
        except Exception:
            pass
        return True
    except Exception:
        return False


def _ensure_vazir():
    d = _font_dir()
    for name, url in _VAZIR_FILES.items():
        p = os.path.join(d, name)
        if not os.path.exists(p):
            try:
                urllib.request.urlretrieve(url, p)
            except Exception:
                continue
        if os.path.exists(p):
            _register_font_file(p)


def setup_fonts(root):
    global FONT, FONT_FA, FONT_EN
    try:
        _ensure_vazir()
        fams = {f.lower(): f for f in tkfont.families(root)}

        def first(cands, default):
            for c in cands:
                if c.lower() in fams:
                    return fams[c.lower()]
            return default
        fa = first(["Vazirmatn", "Vazirmatn UI", "Vazir"], None)
        en = first(["Inter", "SF Pro Text", "Helvetica Neue", "Segoe UI"], None)
        if fa is None:
            fa = first(["Tahoma", "Geeza Pro", "Noto Naskh Arabic", "DejaVu Sans"], en or "Helvetica")
        if en is None:
            en = fa or "Helvetica"
        FONT_FA, FONT_EN, FONT = fa, en, en
    except Exception:
        pass


def _is_rtl_text(text):
    return bool(re.search(r"[؀-ۿ]", text or ""))


def detect_lang():
    if core.UI_LANG:
        return core.UI_LANG
    try:
        loc = (locale.getdefaultlocale()[0] or "").lower()
    except Exception:
        loc = ""
    for code, _, _ in i18n.LANGUAGES:
        if loc.startswith(code):
            return code
    return "en"


class GitAIApp:
    def __init__(self, root):
        self.root = root
        self.repo_path = None
        self.projects = core.load_projects()
        self.pending = None
        self.typing_frame = None
        self._replaying = False
        self.history = self._load_history()

        root.title("git-ai")
        root.geometry("1060x760")
        root.minsize(880, 620)
        root.configure(bg=BG)

        setup_fonts(root)
        i18n.set_language(detect_lang())
        self._init_style()
        self._build()
        if self.history:
            self._replay()
            self.refresh_github_status()
        else:
            self._greet()

    # ------------------------------------------------------------- history
    def _load_history(self):
        try:
            import json
            with open(HISTORY_FILE, encoding="utf-8") as f:
                data = json.load(f)
            return [(k, v) for k, v in data if k in ("user", "bot", "term")][-200:]
        except Exception:
            return []

    def _save_history(self):
        try:
            import json
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.history[-200:], f, ensure_ascii=False)
        except Exception:
            pass

    def _record(self, kind, text_):
        if not self._replaying:
            self.history.append((kind, text_))
            self._save_history()

    def _replay(self):
        self._replaying = True
        for kind, text_ in self.history:
            if kind == "user":
                self.user(text_)
            elif kind == "term":
                self.term(text_)
            else:
                self.bot(text_)
        self._replaying = False

    # ------------------------------------------------------------- styling
    def _init_style(self):
        try:
            ttk.Style().theme_use("clam")
        except tk.TclError:
            pass
        self.root.option_add("*TCombobox*Listbox.background", PANEL)
        self.root.option_add("*TCombobox*Listbox.foreground", INK)
        self.root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#fff")

    def _flatbtn(self, parent, text, cmd, bg=ELEV, fg=INK, hover=ELEV2,
                 font=None, padx=10, pady=5, bold=False):
        f = font or (FONT, 10, "bold" if bold else "normal")
        b = tk.Label(parent, text=text, bg=bg, fg=fg, font=f, cursor="hand2",
                     padx=padx, pady=pady, disabledforeground=MUTED, takefocus=0)
        b._bg, b._hover = bg, hover
        b.bind("<Button-1>", lambda e: (str(b["state"]) != "disabled") and cmd())
        b.bind("<Enter>", lambda e: (str(b["state"]) != "disabled") and b.config(bg=b._hover))
        b.bind("<Leave>", lambda e: b.config(bg=b._bg))
        return b

    # ------------------------------------------------------------- build
    def _build(self):
        self.rtl = i18n.is_rtl()
        self.lead = "right" if self.rtl else "left"
        self.trail = "left" if self.rtl else "right"
        self.bot_side = self.lead
        self.user_side = self.trail
        for w in self.root.winfo_children():
            w.destroy()
        self._build_topbar()
        self._build_footer()
        main = tk.Frame(self.root, bg=BG)
        main.pack(fill="both", expand=True)
        self._build_sidebar(main)
        self._build_chat(main)
        self.render_projects()
        if self.projects:
            self.set_active(self.projects[0], announce=False)

    def _build_topbar(self):
        bar = tk.Frame(self.root, bg=PANEL, height=58)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        tk.Frame(self.root, bg=ACCENT, height=2).pack(fill="x")

        wrap = tk.Frame(bar, bg=PANEL)
        wrap.pack(side=self.lead, padx=18)
        tk.Label(wrap, text="git", bg=PANEL, fg=INK, font=(FONT, 18, "bold")).pack(side="left")
        tk.Label(wrap, text="-ai", bg=PANEL, fg=ACCENT, font=(FONT, 18, "bold")).pack(side="left")
        tk.Label(bar, text=t("subtitle"), bg=PANEL, fg=MUTED,
                 font=((FONT_FA if self.rtl else FONT), 10)).pack(side=self.lead, pady=(4, 0))

        # language switcher
        langs = [native for _, native, _ in i18n.LANGUAGES]
        self.lang_combo = ttk.Combobox(bar, values=langs, state="readonly", width=10)
        self.lang_combo.set(i18n.code_to_name(i18n.get_language()))
        self.lang_combo.pack(side=self.trail, padx=(4, 14))
        self.lang_combo.bind("<<ComboboxSelected>>", self._on_lang_change)

        self._flatbtn(bar, t("btn_settings"), self.open_settings, bg=PANEL, hover=ELEV).pack(side=self.trail, padx=3)
        self._flatbtn(bar, t("btn_about"), self.open_about, bg=PANEL, hover=ELEV).pack(side=self.trail, padx=3)
        self._flatbtn(bar, t("feature_btn"), self.start_feature, bg=PANEL, hover=ELEV).pack(side=self.trail, padx=3)
        self.login_btn = self._flatbtn(bar, t("github_login"), self.github_login, bg=PANEL, hover=ELEV)
        self.login_btn.pack(side=self.trail, padx=3)
        self.star_badge = self._flatbtn(bar, "⭐ …", lambda: webbrowser.open(core.LINK_PROJECT),
                                        bg=ELEV, fg=STAR, hover=ELEV2, bold=True)
        self.star_badge.pack(side=self.trail, padx=3)
        self.refresh_stars()

    def _build_footer(self):
        foot = tk.Frame(self.root, bg=PANEL)
        foot.pack(side="bottom", fill="x")
        tk.Frame(self.root, bg=BORDER, height=1).pack(side="bottom", fill="x")
        lk = tk.Label(foot, text="Power by Noqte", bg=PANEL, fg=MUTED,
                      font=(FONT, 8), cursor="hand2", padx=10, pady=2)
        lk.pack()
        lk.bind("<Button-1>", lambda e: webbrowser.open(NOQTE_URL))
        lk.bind("<Enter>", lambda e: lk.config(fg="#79c0ff"))
        lk.bind("<Leave>", lambda e: lk.config(fg=MUTED))

    def _on_lang_change(self, _e):
        code = i18n.name_to_code(self.lang_combo.get())
        i18n.set_language(code)
        try:
            core.update_env({"GIT_AI_LANG": code})
        except Exception:
            pass
        self._build()
        # Keep the conversation; don't wipe it on language switch.
        if self.history:
            self._replay()
            self.refresh_github_status()
        else:
            self._greet()

    def _build_sidebar(self, parent):
        side = tk.Frame(parent, bg=PANEL, width=230)
        side.pack(side=self.lead, fill="y")
        side.pack_propagate(False)
        tk.Frame(parent, bg=BORDER, width=1).pack(side=self.lead, fill="y")
        anc = "e" if self.rtl else "w"
        tk.Label(side, text=t("side_projects"), bg=PANEL, fg=MUTED,
                 font=(FONT, 9, "bold")).pack(anchor=anc, padx=16, pady=(16, 8))
        self.proj_list = tk.Frame(side, bg=PANEL)
        self.proj_list.pack(fill="both", expand=True, padx=8)
        btns = tk.Frame(side, bg=PANEL)
        btns.pack(fill="x", padx=12, pady=12)
        self._flatbtn(btns, t("side_open"), self.open_project, bg=ELEV, hover=ELEV2,
                      pady=8).pack(fill="x", pady=3)
        self._flatbtn(btns, t("side_new"), self.new_project_dialog, bg=ACCENT, fg="#fff",
                      hover=ACCENT_H, pady=8, bold=True).pack(fill="x", pady=3)

    def render_projects(self):
        for w in self.proj_list.winfo_children():
            w.destroy()
        anc = "e" if self.rtl else "w"
        if not self.projects:
            tk.Label(self.proj_list, text=t("side_none"), bg=PANEL, fg=MUTED, font=(FONT, 9),
                     wraplength=190, justify=("right" if self.rtl else "left")).pack(anchor=anc, padx=8, pady=4)
            return
        for p in self.projects:
            active = (p == self.repo_path)
            bg = ACCENT if active else PANEL
            row = tk.Frame(self.proj_list, bg=bg)
            row.pack(fill="x", pady=2)
            name = os.path.basename(p.rstrip("/")) or p
            fg = "#fff" if active else INK
            dot = "●  " if active else "○  "
            lbl = tk.Label(row, text=dot + name, bg=bg, fg=fg,
                           font=(FONT, 10, "bold" if active else "normal"),
                           anchor=("e" if self.rtl else "w"), cursor="hand2", padx=10, pady=8)
            lbl.pack(side=self.lead, fill="x", expand=True)
            lbl.bind("<Button-1>", lambda e, path=p: self.set_active(path))
            x = tk.Label(row, text="✕", bg=bg, fg=("#fff" if active else MUTED), cursor="hand2", padx=8)
            x.pack(side=self.trail)
            x.bind("<Button-1>", lambda e, path=p: self.remove_project(path))

    # ------------------------------------------------------------- chat
    def _build_chat(self, parent):
        wrap = tk.Frame(parent, bg=BG)
        wrap.pack(side=self.lead, fill="both", expand=True)
        self.active_header = tk.Label(wrap, text=t("hdr_no_project"), bg=PANEL, fg=MUTED,
                                      anchor=("e" if self.rtl else "w"), font=(FONT, 10), padx=16, pady=8)
        self.active_header.pack(fill="x")
        tk.Frame(wrap, bg=BORDER, height=1).pack(fill="x")

        cwrap = tk.Frame(wrap, bg=BG)
        cwrap.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(cwrap, bg=BG, highlightthickness=0)
        self.canvas.pack(side=self.lead, fill="both", expand=True)
        sb = ttk.Scrollbar(cwrap, orient="vertical", command=self.canvas.yview)
        sb.pack(side=self.trail, fill="y")
        self.canvas.configure(yscrollcommand=sb.set)
        self.msgs = tk.Frame(self.canvas, bg=BG)
        self.win = self.canvas.create_window((0, 0), window=self.msgs, anchor="nw")
        self.msgs.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.win, width=e.width))
        self._bind_scroll()

        tb = tk.Frame(wrap, bg=BG)
        tb.pack(fill="x", padx=14, pady=(6, 0))
        for key, cmd in [("tb_status", lambda: self.run_git("git status")),
                         ("tb_commit", self.smart_commit),
                         ("tb_pull", lambda: self.run_git("git pull")),
                         ("tb_push", self.do_push),
                         ("tb_undo", self.undo_last)]:
            self._flatbtn(tb, t(key), cmd, bg=ELEV, hover=ELEV2, font=(FONT, 9),
                          padx=10, pady=5).pack(side=self.lead, padx=3)

        chips = tk.Frame(wrap, bg=BG)
        chips.pack(fill="x", padx=14, pady=(8, 2))
        tk.Label(chips, text=t("try"), bg=BG, fg=MUTED, font=(FONT, 9)).pack(side=self.lead, padx=(0, 6))
        for key in ["chip_changed", "chip_commit", "chip_push", "chip_newproj", "chip_undo"]:
            self._flatbtn(chips, t(key), lambda k=key: self.suggest(t(k)), bg=ELEV,
                          fg="#79c0ff", hover=ELEV2, font=(FONT, 9), padx=10, pady=4).pack(side=self.lead, padx=3)

        row = tk.Frame(wrap, bg=BG)
        row.pack(fill="x", padx=14, pady=12)
        field = tk.Frame(row, bg=ELEV, highlightbackground=BORDER, highlightthickness=1)
        field.pack(side=self.lead, fill="x", expand=True, padx=(0, 10) if not self.rtl else (10, 0))
        self.entry = tk.Entry(field, font=(FONT_FA, 13), bg=ELEV, fg=INK, relief="flat",
                              insertbackground=INK, disabledbackground=ELEV,
                              justify=("right" if self.rtl else "left"))
        self.entry.pack(fill="x", padx=10, ipady=9)
        self.entry.bind("<Return>", lambda e: self.on_send())
        self.entry.bind("<FocusIn>", lambda e: field.config(highlightbackground=ACCENT, highlightcolor=ACCENT))
        self.entry.bind("<FocusOut>", lambda e: field.config(highlightbackground=BORDER, highlightcolor=BORDER))
        self.entry.focus_set()
        self.send_btn = self._flatbtn(row, t("send"), self.on_send, bg=ACCENT, fg="#fff",
                                      hover=ACCENT_H, font=(FONT, 11, "bold"), padx=18, pady=9)
        self.send_btn.pack(side=self.trail)

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
            b = core.get_branch(self.repo_path) or t("no_branch")
            self.active_header.config(text=t("hdr_project", name=os.path.basename(self.repo_path), branch=b), fg=INK)
        else:
            self.active_header.config(text=t("hdr_no_project"), fg=MUTED)

    # --- bubbles ---
    def _bubble(self, text_, side, bg, fg, sender=None, name_fg=MUTED, mono=False):
        rtl = (not mono) and _is_rtl_text(text_)
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
            tk.Label(head, text=sender, bg=BG, fg=name_fg, font=(FONT, 8, "bold")).pack(side="left")
        font = (MONO, 10) if mono else ((FONT_FA if rtl else FONT_EN), 12)
        lbl = tk.Label(col, text=text_, bg=bg, fg=fg, font=font, wraplength=WRAP,
                       justify=("right" if rtl else "left"), anchor="w", padx=15, pady=11)
        lbl.pack(anchor=anchor)
        self._scroll_bottom()
        return row

    def user(self, text_):
        self._bubble(text_, self.user_side, USER_BG, USER_FG, sender="YOU", name_fg=MUTED)
        self._record("user", text_)

    def bot(self, text_):
        self._bubble(text_, self.bot_side, BOT_BG, BOT_FG, sender="git-ai", name_fg="#79c0ff")
        self._record("bot", text_)

    def term(self, text_):
        self._bubble(text_, self.bot_side, TERM_BG, TERM_FG, sender="git-ai · output", name_fg=MUTED, mono=True)
        self._record("term", text_)

    def bot_actions(self, text_, buttons):
        self._record("bot", text_)
        rtl = _is_rtl_text(text_)
        row = tk.Frame(self.msgs, bg=BG)
        row.pack(fill="x", padx=18, pady=(8, 2))
        col = tk.Frame(row, bg=BG)
        col.pack(side=self.bot_side)
        head = tk.Frame(col, bg=BG)
        head.pack(anchor=("e" if self.rtl else "w"), padx=6, pady=(0, 3))
        tk.Label(head, text="✦", bg=BG, fg=ACCENT, font=(FONT, 9)).pack(side="left", padx=(0, 4))
        tk.Label(head, text="git-ai", bg=BG, fg="#79c0ff", font=(FONT, 8, "bold")).pack(side="left")
        box = tk.Frame(col, bg=BOT_BG)
        box.pack(anchor="w")
        tk.Label(box, text=text_, bg=BOT_BG, fg=BOT_FG, font=((FONT_FA if rtl else FONT_EN), 12),
                 wraplength=WRAP, justify=("right" if rtl else "left"), anchor="w",
                 padx=15, pady=11).pack(anchor="w")
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
        self.typing_frame = self._bubble("● ● ●", self.bot_side, BOT_BG, MUTED)

    def _typing_off(self):
        if self.typing_frame:
            self.typing_frame.destroy()
            self.typing_frame = None

    # ------------------------------------------------------------- greet
    def _greet(self):
        self.bot(t("welcome"))
        self.bot_actions(t("star_invite"), [(t("btn_star"), lambda: webbrowser.open(core.LINK_PROJECT))])
        if not self.projects:
            self.bot_actions(t("pick_first"),
                             [(t("side_open"), self.open_project),
                              (t("side_new"), self.new_project_dialog)])
        if core.PROVIDER == "openai" and not core.LLM_API_KEY:
            self.bot_actions(t("nokey_nudge"),
                             [(t("btn_how"), lambda: self.bot(self._setup_text())),
                              (t("btn_signup"), lambda: webbrowser.open(core.BYNARA_SIGNUP_URL)),
                              (t("btn_open_settings"), self.open_settings)])
        self.refresh_github_status()

    # ------------------------------------------------------------- projects
    def open_project(self):
        path = filedialog.askdirectory()
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
        self.bot(t("removed", name=os.path.basename(path)))

    def set_active(self, path, announce=True):
        self.repo_path = path
        self.render_projects()
        self.update_active_header()
        if announce:
            branch = core.get_branch(path)
            if not os.path.isdir(os.path.join(path, ".git")):
                self.bot_actions(t("not_git_offer", name=os.path.basename(path)),
                                 [(t("btn_init"), lambda: self.run_git("git init"))])
            else:
                self.bot(t("switched", name=os.path.basename(path), branch=branch or t("no_branch")))
                if not core.has_remote(path):
                    self.bot_actions(t("no_remote_offer", name=os.path.basename(path)),
                                     [(t("btn_publish"), self.publish_to_github)])

    def new_project_dialog(self):
        self.pending = {"type": "new_repo_name"}
        self.bot(t("ask_name"))

    # ------------------------------------------------------------- send
    def on_send(self):
        text_ = self.entry.get().strip()
        if not text_:
            return
        self.entry.delete(0, "end")
        self.user(text_)
        if self.pending:
            self._resolve_pending(text_)
            return
        if self._FEATURE_RE.search(text_):
            self._start_feature_text(text_)
            return
        if self._PUBLISH_RE.search(text_):
            self.publish_to_github()
            return
        intent = core.detect_intent(text_)
        if intent == "new_repo":
            self._start_new_repo(text_)
        elif intent == "switch_project":
            self._switch_by_text(text_)
        elif self._local_reply(text_):
            return
        else:
            self._chat_assistant(text_)

    def _resolve_pending(self, text_):
        kind = self.pending.get("type")
        self.pending = None
        if kind == "new_repo_name":
            self._create_repo_with_name(text_)
        elif kind == "feature_desc":
            self._confirm_feature(text_)
        elif kind == "confirm":
            cmd = self.pending_cmd if hasattr(self, "pending_cmd") else None

    # --- local replies (greeting / help / author / setup) ---
    _GREET_RE = re.compile(r"^\s*(hi|hello|hey|hiya|yo|howdy|salam|salaam|سلام|درود|bonjour|hola|salut|مرحبا|أهلا)\b", re.I)
    _HELP_RE = re.compile(r"(what can you do|what do you do|who are you|\bhelp\b|چیکار|چی\s?کار|کمک|راهنما|قابلیت|aide|ayuda|مساعدة|ماذا تفعل)", re.I)
    _AUTHOR_RE = re.compile(r"(who (?:made|wrote|created|built)|\bauthor\b|\bcreator\b|سازنده|نویسنده|کی (?:نوشت|ساخت)|چه کسی|qui a (?:fait|créé)|quién|من صنع|من كتب)", re.I)
    _SETUP_RE = re.compile(r"(how (?:do|can) i (?:use|start|set ?up)|get started|set ?up|sign ?up|register|api ?key|چطور|راه\s?انداز|ثبت\s?نام|کلید|clé api|s'inscrire|clave api|registrarse|مفتاح|تسجيل|اشتراك)", re.I)
    _FEATURE_RE = re.compile(r"(feature request|request a feature|suggest|درخواست قابلیت|درخواست ویژگی|پیشنهاد|قابلیت جدید|fonctionnalité|función nueva|sugerencia|ميزة|اقتراح)", re.I)
    _PUBLISH_RE = re.compile(r"(publish|upload to github|put .* on github|منتشر|انتشار|آپلود|بذار رو گیت|publier sur github|publicar en github|نشر على github)", re.I)

    def _local_reply(self, text_):
        if self._AUTHOR_RE.search(text_):
            self.bot(t("author_intro") + "\n"
                     f"• {core.LINK_PROJECT}\n• {core.LINK_GITHUB}\n"
                     f"• Twitter/X: {core.LINK_TWITTER}\n• Instagram: {core.LINK_INSTAGRAM}\n"
                     f"• LinkedIn: {core.LINK_LINKEDIN}")
            self.bot_actions(t("more"),
                             [(t("btn_star"), lambda: webbrowser.open(core.LINK_PROJECT)),
                              (t("btn_about"), self.open_about)])
            return True
        if self._SETUP_RE.search(text_):
            self.bot(self._setup_text())
            self.bot_actions(t("shortcuts"),
                             [(t("btn_signup"), lambda: webbrowser.open(core.BYNARA_SIGNUP_URL)),
                              (t("btn_open_settings"), self.open_settings)])
            return True
        if self._GREET_RE.search(text_):
            self.bot(t("greeting"))
            return True
        if self._HELP_RE.search(text_):
            self.bot(t("help"))
            return True
        return False

    def _setup_text(self):
        s = t("setup", url=core.BYNARA_SIGNUP_URL)
        if not core.LLM_API_KEY:
            s = t("setup_nokey") + s
        return s

    # --- new repo ---
    def _start_new_repo(self, text_):
        m = re.search(r"(?:called|named|name|به ?نام|اسم|nommé|llamado|اسمه)\s+['\"]?([\w.\- ]{1,40})", text_, re.I)
        if m:
            self._create_repo_with_name(m.group(1).strip())
        else:
            self.pending = {"type": "new_repo_name"}
            self.bot(t("ask_name2"))

    def _create_repo_with_name(self, name):
        parent = filedialog.askdirectory()
        if not parent:
            self.bot(t("no_location"))
            return
        path, out = core.create_local_repo(parent, name)
        self.projects = core.add_project(path)
        self.set_active(path, announce=False)
        self.bot(t("created", name=os.path.basename(path)))
        self.term(out)
        self.bot_actions(t("first_commit_q"), [(t("btn_first_commit"), self._first_commit)])

    def _first_commit(self):
        self.run_git("git add -A", silent=True)
        self.run_git('git commit -m "Initial commit"', offer_push=True)

    def _switch_by_text(self, text_):
        match = next((p for p in self.projects if os.path.basename(p).lower() in text_.lower()), None)
        if match:
            self.set_active(match)
        elif self.projects:
            self.bot_actions(t("which_project"),
                             [(os.path.basename(p), lambda path=p: self.set_active(path)) for p in self.projects])
        else:
            self.bot_actions(t("no_projects_actions"),
                             [(t("side_open"), self.open_project), (t("side_new"), self.new_project_dialog)])

    # --- assistant (model) ---
    def _chat_assistant(self, text_):
        if not self.repo_path:
            self.bot_actions(t("pick_then_git"),
                             [(t("side_open"), self.open_project), (t("side_new"), self.new_project_dialog)])
            return
        self._typing_on()
        self.send_btn.config(state="disabled")
        threading.Thread(target=self._assistant_worker, args=(text_,), daemon=True).start()

    def _assistant_worker(self, text_):
        try:
            result = core.assistant_reply(text_, cwd=self.repo_path)
        except Exception as e:
            self.root.after(0, lambda: self._assistant_error(str(e)))
            return
        self.root.after(0, lambda: self._assistant_done(result))

    def _assistant_error(self, msg):
        self._typing_off()
        self.send_btn.config(state="normal")
        self.bot(t("model_unreachable", msg=msg))

    def _assistant_done(self, result):
        self._typing_off()
        self.send_btn.config(state="normal")
        kind_t = result.get("type", "talk")
        reply = result.get("reply", "")
        command = result.get("command", "")
        if kind_t in ("talk", "reject"):
            self.bot(reply or t("help"))
            return
        if reply:
            self.bot(reply)
        if not self.repo_path:
            return
        kind, _ = core.classify_command(command)
        if kind == "invalid":
            self.bot(t("couldnt_form"))
            return
        if kind == "blocked":
            self.bot(t("blocked_unsafe", cmd=command))
            return
        if kind == "dangerous":
            self.bot_actions(t("dangerous_q", cmd=command),
                             [(t("btn_run_it"), lambda: self.run_git(command, dangerous_ok=True)),
                              (t("btn_cancel"), lambda: self.bot(t("cancelled")))])
            return
        self.run_git(command, offer_push=("commit" in command and "push" not in command))

    # ------------------------------------------------------- run + explain
    def run_git(self, command, dangerous_ok=False, silent=False, offer_push=False):
        if not self.repo_path:
            self.bot(t("open_first"))
            return
        kind, _ = core.classify_command(command)
        if kind in ("invalid", "blocked"):
            self.bot(t("blocked_unsafe", cmd=command))
            return
        if kind == "dangerous" and not dangerous_ok:
            self.bot_actions(t("dangerous_q", cmd=command),
                             [(t("btn_run_it"), lambda: self.run_git(command, dangerous_ok=True)),
                              (t("btn_cancel"), lambda: self.bot(t("cancelled")))])
            return
        out = core.run_command_capture(command, cwd=self.repo_path)
        if not silent:
            self.term(f"$ {command}\n{out}")          # raw output stays English
            if core.should_explain(command):           # then a plain-language note
                self._explain_async(command, out)
        self.update_active_header()
        self.render_projects()
        if offer_push and "commit" in command:
            self.bot_actions(t("committed_push_q"),
                             [(t("btn_push_now"), self.do_push),
                              (t("btn_not_now"), lambda: None)])

    def _explain_async(self, command, out):
        threading.Thread(target=self._explain_worker, args=(command, out), daemon=True).start()

    def _explain_worker(self, command, out):
        msg = core.explain_action(command, out, lang=i18n.get_language())
        if msg:
            self.root.after(0, lambda: self.bot(msg))

    def do_push(self):
        if not self.repo_path:
            self.bot(t("open_first"))
            return
        branch = core.get_branch(self.repo_path) or "HEAD"
        self.run_git(f"git push -u origin {branch}")

    def suggest(self, text_):
        self.entry.delete(0, "end")
        self.entry.insert(0, text_)
        self.on_send()

    def undo_last(self):
        if not self.repo_path:
            self.bot(t("open_first"))
            return
        self.bot_actions(t("dangerous_q", cmd="git revert HEAD --no-edit"),
                         [(t("btn_run_it"), lambda: self.run_git("git revert HEAD --no-edit", dangerous_ok=True)),
                          (t("btn_cancel"), lambda: self.bot(t("cancelled")))])

    def smart_commit(self):
        if not self.repo_path:
            self.bot(t("open_first"))
            return
        self.bot(t("looking_changes"))
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
        self.bot_actions(t("commit_drafted", msg=preview),
                         [(t("btn_commit_it"), lambda: self.run_git(cmd, offer_push=True)),
                          (t("btn_commit_push"), lambda: (self.run_git(cmd), self.do_push()))])

    # ------------------------------------------------------- publish flow
    def publish_to_github(self):
        if not self.repo_path:
            self.bot(t("open_first"))
            return
        if not (core.gh_available() and core.gh_account()):
            self.bot(t("publish_need_gh"))
            return
        self.bot_actions(t("publish_offer"),
                         [(t("btn_publish"), self._do_publish),
                          (t("btn_not_now"), lambda: None)])

    def _do_publish(self):
        self.bot(t("publishing"))
        self._typing_on()
        threading.Thread(target=self._publish_worker, daemon=True).start()

    def _publish_worker(self):
        cwd = self.repo_path
        logs = []
        if not os.path.isdir(os.path.join(cwd, ".git")):
            logs.append(core.run_command_capture("git init", cwd))
        if not core.run_git_context_cmd(["git", "log", "--oneline", "-1"], cwd):
            core.run_command_capture("git add -A", cwd)
            logs.append(core.run_command_capture('git commit -m "Initial commit"', cwd))
        name = os.path.basename(cwd.rstrip("/"))
        out = core.run_command_capture(
            f"gh repo create {name} --public --source=. --remote=origin --push", cwd)
        logs.append(out)
        m = re.search(r"https?://github\.com/\S+", out)
        url = m.group(0) if m else None
        self.root.after(0, lambda: self._publish_done("\n".join(logs), url))

    def _publish_done(self, log, url):
        self._typing_off()
        self.term(log)
        if url:
            self.bot(t("publish_done", url=url))
        self.update_active_header()

    # ------------------------------------------------------- feature request
    def start_feature(self):
        self.pending = {"type": "feature_desc"}
        self.bot(t("feature_ask"))

    def _start_feature_text(self, text_):
        # strip a leading trigger word if present, else ask
        self.pending = {"type": "feature_desc"}
        self.bot(t("feature_ask"))

    def _confirm_feature(self, text_):
        self.bot_actions(t("feature_confirm", text=text_),
                         [(t("btn_send_request"), lambda: self._submit_feature(text_)),
                          (t("btn_cancel"), lambda: self.bot(t("cancelled")))])

    def _submit_feature(self, text_):
        self._typing_on()
        threading.Thread(target=self._feature_worker, args=(text_,), daemon=True).start()

    def _feature_worker(self, text_):
        title = "[Feature] " + (text_[:60] + ("…" if len(text_) > 60 else ""))
        body = text_ + "\n\n— submitted from the git-ai app"
        url, ok, _msg = core.create_feature_request(title, body)
        self.root.after(0, lambda: self._feature_done(title, body, url, ok))

    def _feature_done(self, title, body, url, ok):
        self._typing_off()
        if ok and url:
            self.bot(t("feature_done", url=url))
        else:
            webbrowser.open(core.new_issue_url(title, body))
            self.bot(t("feature_browser"))

    # ----------------------------------------------------------- GitHub gh
    def refresh_github_status(self):
        threading.Thread(target=self._gh_status_worker, daemon=True).start()

    def _gh_status_worker(self):
        acct = core.gh_account() if core.gh_available() else None
        def update():
            self.login_btn.config(text=(t("github_signed_in", acct=acct) if acct else t("github_login")),
                                  fg=(OK if acct else INK))
        self.root.after(0, update)

    def github_login(self):
        if not core.gh_available():
            self.bot(t("login_need_gh"))
            return
        if core.gh_account():
            self.bot(t("already_signed", acct=core.gh_account()))
            return
        self.bot(t("login_start"))
        threading.Thread(target=self._gh_login_worker, daemon=True).start()

    def _gh_login_worker(self):
        try:
            proc = subprocess.Popen(
                ["gh", "auth", "login", "--web", "--git-protocol", "https", "--hostname", "github.com"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
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
        self.bot(t("login_code", code=code))

    # --------------------------------------------------------------- about
    def refresh_stars(self):
        threading.Thread(target=self._stars_worker, daemon=True).start()

    def _stars_worker(self):
        n = core.get_repo_stars()
        self.root.after(0, lambda: self.star_badge.config(text=(f"⭐ {n}" if n is not None else "⭐ Star")))

    def open_about(self):
        win = tk.Toplevel(self.root)
        win.title(t("btn_about"))
        win.configure(bg=BG)
        win.geometry("480x560")
        win.transient(self.root)
        win.grab_set()
        tk.Frame(win, bg=ACCENT, height=3).pack(fill="x")
        tk.Label(win, text="git-ai", bg=BG, fg=INK, font=(FONT, 26, "bold")).pack(pady=(24, 0))
        tk.Label(win, text=t("about_subtitle"), bg=BG, fg=MUTED, font=(FONT, 11)).pack()
        star_lbl = tk.Label(win, text="⭐ …", bg=BG, fg=STAR, font=(FONT, 15, "bold"))
        star_lbl.pack(pady=(18, 6))
        threading.Thread(target=lambda: self.root.after(
            0, lambda n=core.get_repo_stars(): star_lbl.config(
                text=(t("about_stars", n=n) if n is not None else t("about_star_btn")))), daemon=True).start()
        self._flatbtn(win, t("about_star_btn"), lambda: webbrowser.open(core.LINK_PROJECT),
                      bg=ACCENT, fg="#fff", hover=ACCENT_H, font=(FONT, 11, "bold"),
                      padx=16, pady=8).pack(pady=(4, 8))
        tk.Label(win, text=t("about_star_note"), bg=BG, fg=MUTED, font=(FONT, 10)).pack()
        tk.Frame(win, bg=BORDER, height=1).pack(fill="x", padx=40, pady=18)
        tk.Label(win, text=t("about_created"), bg=BG, fg=MUTED, font=(FONT, 10)).pack()
        tk.Label(win, text=core.AUTHOR_NAME, bg=BG, fg=INK, font=(FONT, 17, "bold")).pack()
        tk.Label(win, text=t("about_tagline"), bg=BG, fg=VIOLET, font=(FONT, 11, "italic")).pack(pady=(0, 12))
        for label, url in [("🔗 " + core.LINK_PROJECT, core.LINK_PROJECT),
                           ("🐙 GitHub", core.LINK_GITHUB),
                           ("🐦 Twitter/X — @m4tinbeigi", core.LINK_TWITTER),
                           ("📸 Instagram — @m4tinbeigi", core.LINK_INSTAGRAM),
                           ("💼 LinkedIn", core.LINK_LINKEDIN),
                           ("⚡ Power by Noqte", NOQTE_URL)]:
            lk = tk.Label(win, text=label, bg=BG, fg="#79c0ff", cursor="hand2", font=(FONT, 11, "underline"))
            lk.pack(pady=2)
            lk.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))
        self._flatbtn(win, t("about_close"), win.destroy, bg=ELEV, hover=ELEV2, padx=16, pady=6).pack(pady=18)

    # --------------------------------------------------------------- settings
    def open_settings(self):
        win = tk.Toplevel(self.root)
        win.title(t("set_title"))
        win.configure(bg=PANEL)
        win.geometry("540x480")
        win.transient(self.root)
        win.grab_set()
        tk.Frame(win, bg=ACCENT, height=3).pack(fill="x")
        body = tk.Frame(win, bg=PANEL)
        body.pack(fill="both", expand=True, padx=16, pady=10)
        provider = tk.StringVar(value=("openai" if core.PROVIDER == "openai" else "ollama"))

        tk.Label(body, text=t("set_provider"), bg=PANEL, fg=INK, font=(FONT, 11, "bold")).pack(anchor="w", pady=(4, 2))
        prow = tk.Frame(body, bg=PANEL)
        prow.pack(fill="x")
        for val, key in [("ollama", "set_ollama"), ("openai", "set_cloud")]:
            tk.Radiobutton(prow, text=t(key), value=val, variable=provider, bg=PANEL, fg=INK,
                           selectcolor=BG, activebackground=PANEL, activeforeground=INK,
                           highlightthickness=0, font=(FONT, 10)).pack(side="left", padx=(0, 10))

        tk.Label(body, text=t("set_key"), bg=PANEL, fg=INK, font=(FONT, 11, "bold")).pack(anchor="w", pady=(12, 2))
        krow = tk.Frame(body, bg=PANEL)
        krow.pack(fill="x")
        key_entry = tk.Entry(krow, show="•", bg=BG, fg=INK, insertbackground=INK, relief="flat", font=(FONT, 11))
        key_entry.insert(0, core.LLM_API_KEY)
        key_entry.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 6))
        show = tk.BooleanVar(value=False)
        tk.Checkbutton(krow, text=t("set_show"), variable=show, bg=PANEL, fg=INK, selectcolor=BG,
                       activebackground=PANEL, activeforeground=INK, highlightthickness=0, font=(FONT, 10),
                       command=lambda: key_entry.config(show="" if show.get() else "•")).pack(side="left")
        self._flatbtn(body, t("btn_signup"), lambda: webbrowser.open(core.BYNARA_SIGNUP_URL),
                      bg=ELEV, fg="#79c0ff", hover=ELEV2, padx=10, pady=5).pack(anchor="w", pady=(8, 0))

        tk.Label(body, text=t("set_base"), bg=PANEL, fg=MUTED, font=(FONT, 10)).pack(anchor="w", pady=(10, 2))
        base_entry = tk.Entry(body, bg=BG, fg=INK, insertbackground=INK, relief="flat", font=(FONT, 11))
        base_entry.insert(0, core.LLM_BASE_URL or core.BYNARA_BASE_URL)
        base_entry.pack(fill="x", ipady=5)

        tk.Label(body, text=t("set_model"), bg=PANEL, fg=MUTED, font=(FONT, 10)).pack(anchor="w", pady=(10, 2))
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
        self._flatbtn(mrow, t("set_refresh"), refresh_models, bg=ELEV, hover=ELEV2, padx=10, pady=4).pack(side="left", padx=6)

        tk.Label(body, text=t("set_ollama_model"), bg=PANEL, fg=MUTED, font=(FONT, 10)).pack(anchor="w", pady=(10, 2))
        ollama_entry = tk.Entry(body, bg=BG, fg=INK, insertbackground=INK, relief="flat", font=(FONT, 11))
        ollama_entry.insert(0, core.OLLAMA_MODEL)
        ollama_entry.pack(fill="x", ipady=5)

        explain = tk.BooleanVar(value=core.EXPLAIN_ACTIONS)
        tk.Checkbutton(body, text=t("set_explain"), variable=explain, bg=PANEL, fg=INK, selectcolor=BG,
                       activebackground=PANEL, activeforeground=INK, highlightthickness=0,
                       font=(FONT, 10)).pack(anchor="w", pady=(10, 0))

        def save():
            try:
                core.update_env({
                    "PROVIDER": provider.get(), "LLM_API_KEY": key_entry.get().strip(),
                    "LLM_BASE_URL": base_entry.get().strip(), "LLM_MODEL": model_combo.get().strip(),
                    "OLLAMA_MODEL": ollama_entry.get().strip(),
                    "GIT_AI_EXPLAIN": "true" if explain.get() else "false",
                })
            except Exception as e:
                messagebox.showerror("Save failed", str(e))
                return
            self.bot(t("set_saved", provider=core.PROVIDER,
                       model=core.LLM_MODEL if core.PROVIDER == "openai" else core.OLLAMA_MODEL))
            win.destroy()

        btns = tk.Frame(body, bg=PANEL)
        btns.pack(fill="x", pady=16)
        self._flatbtn(btns, t("set_save"), save, bg=ACCENT, fg="#fff", hover=ACCENT_H,
                      font=(FONT, 11, "bold"), padx=16, pady=6).pack(side="right")
        self._flatbtn(btns, t("btn_cancel"), win.destroy, bg=ELEV, hover=ELEV2, padx=16, pady=6).pack(side="right", padx=8)


def main():
    root = tk.Tk()
    GitAIApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
