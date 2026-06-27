#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
git-ai — دستیار گیت با هوش مصنوعی (هسته)
کاربر به زبان طبیعی می‌گوید چه می‌خواهد؛ یک مدل زبانی آن را به یک دستور `git`
تبدیل می‌کند. دستورهای امن خودکار اجرا می‌شوند و دستورهای برگشت‌ناپذیر پیش از
اجرا تأیید می‌گیرند.

این فایل هم به‌صورت خط فرمان (REPL) قابل استفاده است و هم به‌عنوان کتابخانهٔ
مشترک توسط رابط گرافیکی (git_ai_gui.py) فراخوانی می‌شود.

دو حالت اجرا (از فایل .env خوانده می‌شود):
  - ollama : مدل محلی و آفلاین (پیش‌فرض gemma3:4b) — هیچ داده‌ای خارج نمی‌شود.
  - openai : هر سرویس سازگار با OpenAI (/v1/chat/completions) با base_url و کلید کاربر.

هیچ کلید/توکنی در این کد نیست. هر کاربر کلید خودش را در .env می‌گذارد.
"""

import os
import re
import sys
import json
import subprocess
from datetime import datetime

import requests

# ---------------------------------------------------------------------------
# بارگذاری .env (در صورت نبودن python-dotenv بی‌خطا رد می‌شویم)
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ---------------------------------------------------------------------------
# تنظیمات
# ---------------------------------------------------------------------------
PROVIDER = os.getenv("PROVIDER", "ollama").strip().lower()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat").strip()
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b").strip()

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://router.bynara.id/v1").strip().rstrip("/")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini").strip()
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()

# اگر True باشد، دستورهای خطرناک پیش از اجرا تأیید y/n می‌گیرند.
REQUIRE_CONFIRM_FOR_DANGEROUS = True

LOG_FILENAME = "git_ai.log"
REQUEST_TIMEOUT = 120     # ثانیه
MAX_DIFF_CHARS = 6000     # سقف طول diff ارسالی به مدل

# ---------------------------------------------------------------------------
# قوانین ایمنی
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
# system prompt — تبدیل زبان طبیعی به دستور git
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """تو یک دستیار خط فرمان گیت (git) هستی.
کاربر به زبان طبیعی می‌گوید چه می‌خواهد و تو باید آن را به یک دستور کامل و معتبر `git` تبدیل کنی.

قوانین مهم:
- فقط و فقط یک شیء JSON معتبر برگردان. هیچ متن یا بلوک کد اضافه‌ای ننویس.
- ساختار خروجی دقیقاً این باشد:
  {"command": "<دستور کامل git>", "explanation": "<توضیح کوتاه فارسی>"}
- مقدار command همیشه باید با کلمهٔ git شروع شود.
- اگر درخواست مبهم بود، محتمل‌ترین دستور git را انتخاب کن.

نمونه‌ها:
کاربر: همه تغییرات را اضافه کن و با پیام «اصلاح باگ» کامیت کن
خروجی: {"command": "git add -A && git commit -m \\"اصلاح باگ\\"", "explanation": "همهٔ تغییرات را استیج و کامیت می‌کند."}
کاربر: شاخه فعلی را روی origin پوش کن
خروجی: {"command": "git push origin HEAD", "explanation": "شاخهٔ فعلی را روی origin می‌فرستد."}
کاربر: وضعیت مخزن را نشانم بده
خروجی: {"command": "git status", "explanation": "وضعیت فعلی مخزن را نمایش می‌دهد."}
"""

# system prompt — تولید پیام کامیت از روی diff
COMMIT_MSG_SYSTEM_PROMPT = """تو یک دستیار نوشتن «پیام کامیت» گیت هستی.
بر اساس تغییرات (diff و وضعیت) که به تو داده می‌شود، یک پیام کامیت تمیز و معنادار بنویس.

قوانین مهم:
- فقط و فقط یک شیء JSON معتبر برگردان:
  {"title": "<عنوان کوتاه و امری، خط اول، حداکثر حدود ۷۲ کاراکتر>", "description": "<توضیح اختیاری چند خطی دربارهٔ چرایی و جزئیات تغییر>"}
- عنوان را به سبک Conventional Commits بنویس (مثلاً: feat: ... یا fix: ... یا docs: ...).
- اگر تغییر کوچک بود، description می‌تواند خالی باشد ("").
- زبان توضیح را با زبان غالب پروژه یا پیام کاربر هماهنگ کن (پیش‌فرض فارسی).
"""


# ---------------------------------------------------------------------------
# اجرای دستورهای کمکی گیت
# ---------------------------------------------------------------------------
def run_git_context_cmd(args, cwd=None):
    """یک دستور را اجرا و خروجی استانداردش را برمی‌گرداند (برای جمع‌آوری context)."""
    try:
        out = subprocess.run(args, capture_output=True, text=True, timeout=20, cwd=cwd)
        return (out.stdout or "").strip()
    except Exception:
        return ""


def get_branch(cwd=None):
    return run_git_context_cmd(["git", "branch", "--show-current"], cwd)


def gather_repo_context(cwd=None):
    """شاخهٔ فعلی، وضعیت کوتاه و سه کامیت آخر را جمع می‌کند."""
    branch = get_branch(cwd)
    status = run_git_context_cmd(["git", "status", "--short"], cwd)
    log = run_git_context_cmd(["git", "log", "--oneline", "-3"], cwd)
    return (
        "زمینهٔ مخزن فعلی:\n"
        f"شاخهٔ فعلی: {branch or '(نامشخص / خارج از مخزن گیت)'}\n"
        f"وضعیت کوتاه:\n{status or '(بدون تغییر)'}\n"
        f"سه کامیت آخر:\n{log or '(بدون کامیت)'}"
    )


def extract_json(text):
    """پارس مقاوم JSON: کل متن، و در صورت نیاز اولین بلوک {...} با regex."""
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
    raise ValueError("پاسخ مدل JSON معتبر نبود.")


# ---------------------------------------------------------------------------
# فراخوانی مدل‌ها
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
        raise RuntimeError("کلید LLM_API_KEY تنظیم نشده است. آن را در فایل .env قرار دهید.")
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


def _ask(user_content, system_prompt=SYSTEM_PROMPT):
    if PROVIDER == "openai":
        return call_openai(user_content, system_prompt)
    return call_ollama(user_content, system_prompt)


def ask_model(user_prompt, cwd=None):
    """درخواست زبان طبیعی → {command, explanation}."""
    context = gather_repo_context(cwd)
    return _ask(f"{context}\n\nدرخواست کاربر: {user_prompt}")


def generate_commit_message(cwd=None, hint=""):
    """از روی تغییرات استیج‌شده (یا کل تغییرات) یک پیام کامیت تولید می‌کند.
    خروجی: {"title": str, "description": str}
    """
    diff = run_git_context_cmd(["git", "diff", "--staged"], cwd)
    if not diff:
        # اگر چیزی استیج نشده، از کل تغییرات کاری استفاده کن.
        diff = run_git_context_cmd(["git", "diff"], cwd)
    status = run_git_context_cmd(["git", "status", "--short"], cwd)

    if not diff and not status:
        raise ValueError("هیچ تغییری برای ساخت پیام کامیت پیدا نشد.")

    if len(diff) > MAX_DIFF_CHARS:
        diff = diff[:MAX_DIFF_CHARS] + "\n... (بریده شد)"

    user_content = (
        f"وضعیت فایل‌ها:\n{status or '(نامشخص)'}\n\n"
        f"تغییرات (diff):\n{diff or '(diff موجود نیست)'}"
    )
    if hint:
        user_content += f"\n\nراهنمای کاربر برای پیام: {hint}"

    result = _ask(user_content, COMMIT_MSG_SYSTEM_PROMPT)
    return {
        "title": (result.get("title") or "").strip(),
        "description": (result.get("description") or "").strip(),
    }


# ---------------------------------------------------------------------------
# توابع GitHub CLI (gh) — برای رابط گرافیکی
# ---------------------------------------------------------------------------
def gh_available():
    """آیا ابزار gh نصب است؟"""
    try:
        subprocess.run(["gh", "--version"], capture_output=True, text=True, timeout=10)
        return True
    except Exception:
        return False


def gh_account():
    """نام کاربری گیت‌هابِ واردشده را برمی‌گرداند یا None."""
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
    """لیست مخازن کاربر را برمی‌گرداند (nameWithOwner)."""
    try:
        out = subprocess.run(
            ["gh", "repo", "list", "--limit", str(limit),
             "--json", "nameWithOwner", "--jq", ".[].nameWithOwner"],
            capture_output=True, text=True, timeout=30,
        )
        lines = [l.strip() for l in (out.stdout or "").splitlines() if l.strip()]
        return lines
    except Exception:
        return []


# ---------------------------------------------------------------------------
# ایمنی و اجرا
# ---------------------------------------------------------------------------
def classify_command(command):
    """دستور را دسته‌بندی می‌کند: 'blocked' | 'invalid' | 'dangerous' | 'safe'."""
    cmd = (command or "").strip()
    if not cmd:
        return "invalid", "دستوری تولید نشد."
    if not cmd.startswith("git"):
        return "invalid", "فقط دستورهایی که با git شروع می‌شوند اجرا می‌شوند."
    for pat in BLOCKED_PATTERNS:
        if re.search(pat, cmd):
            return "blocked", f"دستور مسدود است (الگوی خطرناک: {pat})."
    for pat in DANGEROUS_PATTERNS:
        if re.search(pat, cmd):
            return "dangerous", f"این دستور برگشت‌ناپذیر یا پرخطر است (الگو: {pat})."
    return "safe", "امن"


def log_command(command, cwd=None):
    """دستور اجراشده را با تاریخ در git_ai.log (داخل پوشهٔ پروژه) ثبت می‌کند."""
    try:
        path = os.path.join(cwd or os.getcwd(), LOG_FILENAME)
        with open(path, "a", encoding="utf-8") as f:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{ts}] {command}\n")
    except Exception:
        pass


def run_command_capture(command, cwd=None):
    """دستور را اجرا و خروجی (stdout+stderr) را به‌صورت متن برمی‌گرداند (برای GUI)."""
    log_command(command, cwd)
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=cwd)
        out = (result.stdout or "") + (result.stderr or "")
        if result.returncode != 0:
            out += f"\n⚠️ کد خروج: {result.returncode}"
        return out.strip() or "(بدون خروجی)"
    except Exception as e:
        return f"❌ خطا در اجرای دستور: {e}"


def execute_command(command, cwd=None):
    """دستور git را اجرا و خروجی را چاپ می‌کند (برای CLI)."""
    log_command(command, cwd)
    try:
        result = subprocess.run(command, shell=True, text=True, cwd=cwd)
        if result.returncode != 0:
            print(f"⚠️  دستور با کد خروج {result.returncode} پایان یافت.")
    except Exception as e:
        print(f"❌ خطا در اجرای دستور: {e}")


# ---------------------------------------------------------------------------
# جریان CLI
# ---------------------------------------------------------------------------
def confirm(prompt):
    try:
        ans = input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return ans in ("y", "yes", "بله", "آره")


def handle_request(user_prompt):
    try:
        result = ask_model(user_prompt)
    except requests.exceptions.ConnectionError:
        if PROVIDER == "openai":
            print(f"❌ اتصال به سرور برقرار نشد. base_url را بررسی کنید: {LLM_BASE_URL}")
        else:
            print(f"❌ اتصال به Ollama برقرار نشد. آیا روی {OLLAMA_URL} در حال اجراست؟")
        return
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response is not None else "?"
        if code in (401, 403):
            print("❌ کلید API نامعتبر است یا دسترسی ندارید (خطای احراز هویت).")
        else:
            print(f"❌ خطای سرور (کد {code}).")
        return
    except RuntimeError as e:
        print(f"❌ {e}")
        return
    except ValueError as e:
        print(f"❌ {e}")
        return
    except Exception as e:
        print(f"❌ خطای غیرمنتظره: {e}")
        return

    command = (result.get("command") or "").strip()
    explanation = (result.get("explanation") or "").strip()
    print(f"\n💡 دستور پیشنهادی: {command}")
    if explanation:
        print(f"   توضیح: {explanation}")

    kind, msg = classify_command(command)
    if kind in ("invalid", "blocked"):
        print(f"⛔ اجرا نشد: {msg}")
        return
    if kind == "dangerous":
        print(f"⚠️  هشدار: {msg}")
        if REQUIRE_CONFIRM_FOR_DANGEROUS and not confirm("آیا مطمئن هستید؟ اجرا شود؟ (y/n): "):
            print("لغو شد.")
            return
        execute_command(command)
        return
    print("✅ اجرا...")
    execute_command(command)


EXIT_WORDS = {"exit", "quit", "خروج", "q"}


def repl():
    print("=" * 60)
    print("  git-ai — دستیار گیت با هوش مصنوعی")
    if PROVIDER == "openai":
        print(f"  حالت: openai  |  مدل: {LLM_MODEL}  |  {LLM_BASE_URL}")
    else:
        print(f"  حالت: ollama  |  مدل: {OLLAMA_MODEL}  |  {OLLAMA_URL}")
    print("  برای خروج: exit / quit / خروج")
    print("=" * 60)
    while True:
        try:
            user_prompt = input("\n🤖 چه می‌خواهی؟ ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nخدانگهدار!")
            break
        if not user_prompt:
            continue
        if user_prompt.lower() in EXIT_WORDS:
            print("خدانگهدار!")
            break
        handle_request(user_prompt)


def main():
    if len(sys.argv) > 1:
        handle_request(" ".join(sys.argv[1:]))
        return
    repl()


if __name__ == "__main__":
    main()
