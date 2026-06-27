#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
git-ai — رابط گرافیکی کامل (Tkinter)

امکانات:
  • انتخاب پوشهٔ پروژه (مخزن گیت) و اعمال همهٔ دستورها روی همان پروژه
  • دکمه‌های سریع: وضعیت، افزودن همه، کامیت، پول، پوش، واکشی
  • لاگین گیت‌هاب با gh، شناسایی خودکار اکانت و واکشی لیست مخازن (و کلون)
  • تولید خودکار «عنوان و توضیح کامیت» با AI از روی تغییرات واقعی (diff)
    + امکان ویرایش دستی و «بازنویسی» توسط AI
  • باکس زبان طبیعی: درخواست فارسی → دستور git با بررسی‌های ایمنی

از منطق هستهٔ git_ai استفاده می‌کند. هیچ کلید/توکنی در کد نیست.
"""

import os
import re
import threading
import webbrowser
import subprocess
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog

import git_ai as core


class GitAIApp:
    def __init__(self, root):
        self.root = root
        self.repo_path = None  # پوشهٔ پروژهٔ انتخاب‌شده
        root.title("git-ai — دستیار گیت با هوش مصنوعی")
        root.geometry("900x720")
        root.minsize(760, 600)

        self._build_topbar()
        self._build_repo_row()
        self._build_github_row()
        self._build_actions_row()
        self._build_commit_box()
        self._build_nl_box()
        self._build_output()

        self.log("به git-ai خوش آمدید. ابتدا یک «پروژه» انتخاب کنید.\n")
        self.refresh_github_status()

    # ------------------------------------------------------------------ UI
    def _build_topbar(self):
        mode = core.PROVIDER
        model = core.LLM_MODEL if mode == "openai" else core.OLLAMA_MODEL
        bar = tk.Label(
            self.root,
            text=f"git-ai   |   حالت مدل: {mode}   |   مدل: {model}",
            font=("Helvetica", 11, "bold"), anchor="e", fg="#333",
        )
        bar.pack(fill="x", padx=10, pady=(10, 2))

    def _build_repo_row(self):
        frame = tk.LabelFrame(self.root, text="پروژه", padx=8, pady=6)
        frame.pack(fill="x", padx=10, pady=4)

        tk.Button(frame, text="📁 انتخاب پروژه", command=self.choose_repo).pack(side="left")
        self.repo_label = tk.Label(frame, text="(هیچ پروژه‌ای انتخاب نشده)", anchor="w", fg="#666")
        self.repo_label.pack(side="left", fill="x", expand=True, padx=8)
        self.branch_label = tk.Label(frame, text="", fg="#0a7", font=("Helvetica", 10, "bold"))
        self.branch_label.pack(side="right")

    def _build_github_row(self):
        frame = tk.LabelFrame(self.root, text="گیت‌هاب", padx=8, pady=6)
        frame.pack(fill="x", padx=10, pady=4)

        self.gh_status_label = tk.Label(frame, text="در حال بررسی...", anchor="w", fg="#666")
        self.gh_status_label.pack(side="left", fill="x", expand=True)

        tk.Button(frame, text="🔑 ورود به گیت‌هاب", command=self.github_login).pack(side="left", padx=4)
        tk.Button(frame, text="↻ واکشی مخازن", command=self.fetch_repos).pack(side="left", padx=4)

        self.repo_combo = ttk.Combobox(frame, width=32, state="readonly")
        self.repo_combo.pack(side="left", padx=4)
        tk.Button(frame, text="⬇ کلون", command=self.clone_selected).pack(side="left", padx=4)

    def _build_actions_row(self):
        frame = tk.LabelFrame(self.root, text="عملیات سریع گیت", padx=8, pady=6)
        frame.pack(fill="x", padx=10, pady=4)
        actions = [
            ("وضعیت", lambda: self.git("git status")),
            ("افزودن همه", lambda: self.git("git add -A")),
            ("واکشی", lambda: self.git("git fetch")),
            ("پول", lambda: self.git("git pull")),
            ("پوش", self.do_push),
        ]
        for text, cmd in actions:
            tk.Button(frame, text=text, width=11, command=cmd).pack(side="left", padx=3)

    def _build_commit_box(self):
        frame = tk.LabelFrame(self.root, text="کامیت با پیام هوشمند", padx=8, pady=6)
        frame.pack(fill="x", padx=10, pady=4)

        row1 = tk.Frame(frame)
        row1.pack(fill="x")
        tk.Label(row1, text="عنوان:").pack(side="left")
        self.commit_title = tk.Entry(row1, font=("Helvetica", 11))
        self.commit_title.pack(side="left", fill="x", expand=True, padx=6, ipady=3)

        tk.Label(frame, text="توضیحات:").pack(anchor="w", pady=(6, 0))
        self.commit_desc = tk.Text(frame, height=4, font=("Helvetica", 10), wrap="word")
        self.commit_desc.pack(fill="x", pady=(0, 6))

        row2 = tk.Frame(frame)
        row2.pack(fill="x")
        tk.Button(row2, text="✨ تولید پیام با AI", command=lambda: self.gen_commit_msg(False)).pack(side="left", padx=3)
        tk.Button(row2, text="🔁 بازنویسی", command=lambda: self.gen_commit_msg(True)).pack(side="left", padx=3)
        tk.Button(row2, text="✅ کامیت", command=self.do_commit).pack(side="left", padx=3)
        tk.Button(row2, text="🚀 کامیت و پوش", command=self.do_commit_push).pack(side="left", padx=3)

    def _build_nl_box(self):
        frame = tk.LabelFrame(self.root, text="درخواست به زبان طبیعی", padx=8, pady=6)
        frame.pack(fill="x", padx=10, pady=4)
        self.nl_entry = tk.Entry(frame, font=("Helvetica", 11), justify="right")
        self.nl_entry.pack(side="left", fill="x", expand=True, ipady=4)
        self.nl_entry.bind("<Return>", lambda e: self.nl_submit())
        self.nl_btn = tk.Button(frame, text="ارسال", width=10, command=self.nl_submit)
        self.nl_btn.pack(side="right", padx=(6, 0))

    def _build_output(self):
        self.output = scrolledtext.ScrolledText(self.root, font=("Menlo", 10), wrap="word", height=12)
        self.output.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        self.output.configure(state="disabled")

    # -------------------------------------------------------------- helpers
    def log(self, text):
        self.output.configure(state="normal")
        self.output.insert("end", text + "\n")
        self.output.see("end")
        self.output.configure(state="disabled")

    def require_repo(self):
        if not self.repo_path:
            messagebox.showwarning("پروژه انتخاب نشده", "ابتدا با «انتخاب پروژه» یک مخزن گیت انتخاب کنید.")
            return False
        return True

    def refresh_branch(self):
        if self.repo_path:
            b = core.get_branch(self.repo_path)
            self.branch_label.config(text=(f"⎇ {b}" if b else "(خارج از مخزن گیت)"))

    # ----------------------------------------------------------- repo logic
    def choose_repo(self):
        path = filedialog.askdirectory(title="پوشهٔ پروژه را انتخاب کنید")
        if not path:
            return
        self.repo_path = path
        self.repo_label.config(text=path, fg="#000")
        is_git = os.path.isdir(os.path.join(path, ".git"))
        if not is_git:
            self.log(f"⚠️ توجه: این پوشه مخزن گیت نیست. برای شروع می‌توانید «git init» بزنید.")
        self.refresh_branch()
        self.log(f"📁 پروژه انتخاب شد: {path}")

    # --------------------------------------------------------- git commands
    def git(self, command, dangerous_ok=False):
        """اجرای یک دستور git روی پروژهٔ انتخابی، با بررسی ایمنی."""
        if not self.require_repo():
            return
        kind, msg = core.classify_command(command)
        if kind in ("invalid", "blocked"):
            self.log(f"⛔ اجرا نشد: {msg}")
            return
        if kind == "dangerous" and not dangerous_ok:
            if core.REQUIRE_CONFIRM_FOR_DANGEROUS:
                if not messagebox.askyesno("تأیید دستور خطرناک", f"{command}\n\n{msg}\n\nاجرا شود؟"):
                    self.log("لغو شد.")
                    return
        self.log(f"$ {command}")
        out = core.run_command_capture(command, cwd=self.repo_path)
        self.log(out + "\n")
        self.refresh_branch()

    def do_push(self):
        if not self.require_repo():
            return
        branch = core.get_branch(self.repo_path) or "HEAD"
        # اگر upstream تنظیم نشده باشد، با -u تنظیم می‌کنیم.
        self.git(f"git push -u origin {branch}")

    def do_commit(self):
        if not self.require_repo():
            return
        title = self.commit_title.get().strip()
        desc = self.commit_desc.get("1.0", "end").strip()
        if not title:
            messagebox.showwarning("عنوان خالی", "عنوان کامیت را وارد کنید یا با AI تولید کنید.")
            return
        # ساخت دستور کامیت با مدیریت گیومه
        safe_title = title.replace('"', '\\"')
        cmd = f'git commit -m "{safe_title}"'
        if desc:
            safe_desc = desc.replace('"', '\\"')
            cmd += f' -m "{safe_desc}"'
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
            hint = (self.commit_title.get().strip() + " " + self.commit_desc.get("1.0", "end").strip()).strip()
        self.log("✨ در حال تولید پیام کامیت از روی تغییرات...")
        threading.Thread(target=self._gen_commit_worker, args=(hint,), daemon=True).start()

    def _gen_commit_worker(self, hint):
        try:
            result = core.generate_commit_message(cwd=self.repo_path, hint=hint)
        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ {e}\n"))
            return
        self.root.after(0, lambda: self._fill_commit_msg(result))

    def _fill_commit_msg(self, result):
        self.commit_title.delete(0, "end")
        self.commit_title.insert(0, result.get("title", ""))
        self.commit_desc.delete("1.0", "end")
        self.commit_desc.insert("1.0", result.get("description", ""))
        self.log("✅ پیام کامیت تولید شد. می‌توانید ویرایش کنید و بعد «کامیت» را بزنید.\n")

    # ----------------------------------------------------------- GitHub (gh)
    def refresh_github_status(self):
        threading.Thread(target=self._gh_status_worker, daemon=True).start()

    def _gh_status_worker(self):
        if not core.gh_available():
            self.root.after(0, lambda: self.gh_status_label.config(
                text="ابزار gh نصب نیست. از https://cli.github.com نصب کنید.", fg="#c00"))
            return
        acct = core.gh_account()
        if acct:
            self.root.after(0, lambda: self.gh_status_label.config(
                text=f"✓ واردشده به‌عنوان: {acct}", fg="#0a7"))
        else:
            self.root.after(0, lambda: self.gh_status_label.config(
                text="وارد نشده‌اید. روی «ورود به گیت‌هاب» بزنید.", fg="#c00"))

    def github_login(self):
        if not core.gh_available():
            messagebox.showinfo("gh نصب نیست", "ابتدا GitHub CLI را از https://cli.github.com نصب کنید.")
            return
        self.log("🔑 شروع فرایند ورود به گیت‌هاب...")
        threading.Thread(target=self._gh_login_worker, daemon=True).start()

    def _gh_login_worker(self):
        try:
            proc = subprocess.Popen(
                ["gh", "auth", "login", "--web", "--git-protocol", "https", "--hostname", "github.com"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            )
            try:
                proc.stdin.write("\n")  # رد کردن «Press Enter to open...»
                proc.stdin.flush()
            except Exception:
                pass

            code = None
            for line in iter(proc.stdout.readline, ""):
                line = line.strip()
                if not line:
                    continue
                m = re.search(r"one-time code:?\s*([A-Z0-9-]{6,})", line)
                if m and not code:
                    code = m.group(1)
                    self.root.after(0, lambda c=code: self._show_login_code(c))
            proc.wait(timeout=300)
        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ خطا در ورود: {e}"))
        finally:
            self.root.after(0, self.refresh_github_status)
            self.root.after(0, lambda: self.log("— فرایند ورود پایان یافت. وضعیت به‌روزرسانی شد."))

    def _show_login_code(self, code):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(code)
        except Exception:
            pass
        self.log(f"🔑 کد یک‌بارمصرف: {code}  (در کلیپ‌بورد کپی شد)")
        webbrowser.open("https://github.com/login/device")
        messagebox.showinfo(
            "کد ورود گیت‌هاب",
            f"کد زیر در کلیپ‌بورد کپی شد:\n\n{code}\n\n"
            "در مرورگرِ بازشده آن را وارد و Authorize کنید.",
        )

    def fetch_repos(self):
        if not core.gh_account():
            messagebox.showinfo("ورود لازم است", "ابتدا وارد گیت‌هاب شوید.")
            return
        self.log("↻ در حال واکشی لیست مخازن...")
        threading.Thread(target=self._fetch_repos_worker, daemon=True).start()

    def _fetch_repos_worker(self):
        repos = core.gh_list_repos()
        def update():
            self.repo_combo["values"] = repos
            if repos:
                self.repo_combo.current(0)
                self.log(f"✓ {len(repos)} مخزن واکشی شد.\n")
            else:
                self.log("هیچ مخزنی پیدا نشد.\n")
        self.root.after(0, update)

    def clone_selected(self):
        repo = self.repo_combo.get().strip()
        if not repo:
            messagebox.showinfo("انتخاب مخزن", "ابتدا یک مخزن از فهرست انتخاب کنید.")
            return
        dest = filedialog.askdirectory(title="پوشهٔ مقصد برای کلون را انتخاب کنید")
        if not dest:
            return
        self.log(f"⬇ در حال کلون {repo} ...")
        threading.Thread(target=self._clone_worker, args=(repo, dest), daemon=True).start()

    def _clone_worker(self, repo, dest):
        out = core.run_command_capture(f"gh repo clone {repo}", cwd=dest)
        name = repo.split("/")[-1]
        cloned_path = os.path.join(dest, name)
        def update():
            self.log(out + "\n")
            if os.path.isdir(os.path.join(cloned_path, ".git")):
                self.repo_path = cloned_path
                self.repo_label.config(text=cloned_path, fg="#000")
                self.refresh_branch()
                self.log(f"📁 پروژه روی مخزن کلون‌شده تنظیم شد: {cloned_path}\n")
        self.root.after(0, update)

    # ------------------------------------------------- natural-language box
    def nl_submit(self):
        if not self.require_repo():
            return
        prompt = self.nl_entry.get().strip()
        if not prompt:
            return
        self.nl_entry.delete(0, "end")
        self.log(f"🤖 درخواست: {prompt}")
        self.nl_btn.config(state="disabled", text="...")
        threading.Thread(target=self._nl_worker, args=(prompt,), daemon=True).start()

    def _nl_worker(self, prompt):
        try:
            result = core.ask_model(prompt, cwd=self.repo_path)
        except Exception as e:
            self.root.after(0, lambda: self._nl_done(error=str(e)))
            return
        self.root.after(0, lambda: self._nl_handle(result))

    def _nl_handle(self, result):
        self.nl_btn.config(state="normal", text="ارسال")
        command = (result.get("command") or "").strip()
        explanation = (result.get("explanation") or "").strip()
        self.log(f"💡 دستور: {command}")
        if explanation:
            self.log(f"   توضیح: {explanation}")
        self.git(command)

    def _nl_done(self, error=""):
        self.nl_btn.config(state="normal", text="ارسال")
        if error:
            self.log(f"❌ خطا: {error}\n")


def main():
    root = tk.Tk()
    GitAIApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
