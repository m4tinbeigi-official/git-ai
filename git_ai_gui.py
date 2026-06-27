#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
git-ai — رابط گرافیکی سبک (Tkinter)
کادر ورودی + دکمه + نمایش خروجی. از همان منطق هستهٔ git_ai استفاده می‌کند.

دستورهای امن خودکار اجرا می‌شوند؛ دستورهای خطرناک پیش از اجرا یک پنجرهٔ تأیید
نشان می‌دهند؛ دستورهای مسدود/نامعتبر اجرا نمی‌شوند.
"""

import threading
import subprocess
import tkinter as tk
from tkinter import scrolledtext, messagebox

import git_ai  # استفادهٔ مجدد از منطق هسته


def run_command_capture(command: str) -> str:
    """دستور را اجرا و خروجی (stdout+stderr) را به صورت متن برمی‌گرداند."""
    git_ai.log_command(command)
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True
        )
        out = (result.stdout or "") + (result.stderr or "")
        if result.returncode != 0:
            out += f"\n⚠️ کد خروج: {result.returncode}"
        return out.strip() or "(بدون خروجی)"
    except Exception as e:
        return f"❌ خطا در اجرای دستور: {e}"


class GitAIApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("git-ai — دستیار گیت")
        root.geometry("720x520")

        mode = git_ai.PROVIDER
        model = git_ai.LLM_MODEL if mode == "openai" else git_ai.OLLAMA_MODEL
        header = tk.Label(
            root,
            text=f"git-ai   |   حالت: {mode}   |   مدل: {model}",
            font=("Helvetica", 11, "bold"),
            anchor="e",
        )
        header.pack(fill="x", padx=10, pady=(10, 4))

        # ورودی
        input_frame = tk.Frame(root)
        input_frame.pack(fill="x", padx=10)

        self.entry = tk.Entry(input_frame, font=("Helvetica", 12), justify="right")
        self.entry.pack(side="left", fill="x", expand=True, ipady=6)
        self.entry.bind("<Return>", lambda e: self.on_submit())

        self.btn = tk.Button(input_frame, text="ارسال", command=self.on_submit, width=10)
        self.btn.pack(side="right", padx=(8, 0))

        # خروجی
        self.output = scrolledtext.ScrolledText(
            root, font=("Menlo", 11), wrap="word", height=20
        )
        self.output.pack(fill="both", expand=True, padx=10, pady=10)
        self.output.configure(state="disabled")

        self.log("به git-ai خوش آمدید. درخواست خود را به فارسی بنویسید و «ارسال» را بزنید.\n")
        self.entry.focus_set()

    def log(self, text: str) -> None:
        self.output.configure(state="normal")
        self.output.insert("end", text + "\n")
        self.output.see("end")
        self.output.configure(state="disabled")

    def on_submit(self) -> None:
        prompt = self.entry.get().strip()
        if not prompt:
            return
        self.entry.delete(0, "end")
        self.log(f"🤖 درخواست: {prompt}")
        self.btn.configure(state="disabled", text="...")
        # فراخوانی مدل در ترد جدا تا رابط فریز نشود.
        threading.Thread(target=self._process, args=(prompt,), daemon=True).start()

    def _process(self, prompt: str) -> None:
        try:
            result = git_ai.ask_model(prompt)
        except Exception as e:
            self.root.after(0, lambda: self._done(error=str(e)))
            return
        self.root.after(0, lambda: self._handle_result(result))

    def _handle_result(self, result: dict) -> None:
        self.btn.configure(state="normal", text="ارسال")
        command = (result.get("command") or "").strip()
        explanation = (result.get("explanation") or "").strip()

        self.log(f"💡 دستور پیشنهادی: {command}")
        if explanation:
            self.log(f"   توضیح: {explanation}")

        kind, msg = git_ai.classify_command(command)

        if kind in ("invalid", "blocked"):
            self.log(f"⛔ اجرا نشد: {msg}\n")
            return

        if kind == "dangerous":
            self.log(f"⚠️ هشدار: {msg}")
            if git_ai.REQUIRE_CONFIRM_FOR_DANGEROUS:
                ok = messagebox.askyesno(
                    "تأیید دستور خطرناک",
                    f"این دستور برگشت‌ناپذیر است:\n\n{command}\n\n{msg}\n\nاجرا شود؟",
                )
                if not ok:
                    self.log("لغو شد.\n")
                    return
            self._run(command)
            return

        # safe
        self.log("✅ اجرا...")
        self._run(command)

    def _run(self, command: str) -> None:
        out = run_command_capture(command)
        self.log(out + "\n")

    def _done(self, error: str = "") -> None:
        self.btn.configure(state="normal", text="ارسال")
        if error:
            self.log(f"❌ خطا: {error}\n")


def main() -> None:
    root = tk.Tk()
    GitAIApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
