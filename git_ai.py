#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
git-ai — دستیار گیت با هوش مصنوعی
کاربر به زبان طبیعی (فارسی یا هر زبانی) می‌گوید چه می‌خواهد؛ یک مدل زبانی آن را
به یک دستور `git` تبدیل می‌کند. دستورهای امن خودکار اجرا می‌شوند و دستورهای
برگشت‌ناپذیر پیش از اجرا تأیید می‌گیرند.

دو حالت اجرا (از فایل .env خوانده می‌شود):
  - ollama : مدل محلی و آفلاین (پیش‌فرض gemma3:4b) — هیچ داده‌ای از سیستم خارج نمی‌شود.
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
    # python-dotenv نصب نیست؛ از متغیرهای محیطی موجود استفاده می‌کنیم.
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

LOG_FILE = os.path.join(os.getcwd(), "git_ai.log")
REQUEST_TIMEOUT = 120  # ثانیه

# ---------------------------------------------------------------------------
# قوانین ایمنی
# ---------------------------------------------------------------------------
# الگوهایی که هرگز نباید اجرا شوند (حتی با تأیید کاربر).
BLOCKED_PATTERNS = [
    r"\brm\b",            # حذف فایل
    r"\bsudo\b",          # اجرای با دسترسی ریشه
    r"\bmkfs\b",          # فرمت دیسک
    r">\s*/dev/",         # نوشتن روی دستگاه‌ها
    r":\(\)\s*\{",        # fork-bomb کلاسیک  :(){ :|:& };:
    r"\bdd\b\s+if=",      # کپی سطح‌پایین خطرناک
    r"\bshutdown\b",
    r"\breboot\b",
]

# الگوهای خطرناک گیت — پیش از اجرا تأیید می‌گیرند.
DANGEROUS_PATTERNS = [
    r"reset\s+--hard",
    r"push\s+.*--force",
    r"push\s+.*\s-f\b",
    r"push\s+-f\b",
    r"clean\s+-[a-z]*f",
    r"branch\s+-D\b",
    r"checkout\s+--\s",
    r"\brestore\b",
    r"filter-branch",
    r"reflog\s+expire",
    r"gc\s+.*--prune",
    r"\brebase\b",
    r"stash\s+(drop|clear)",
    r"update-ref\s+-d",
]

# ---------------------------------------------------------------------------
# system prompt — مدل را وادار می‌کند فقط JSON برگرداند.
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """تو یک دستیار خط فرمان گیت (git) هستی.
کاربر به زبان طبیعی می‌گوید چه می‌خواهد و تو باید آن را به یک دستور کامل و معتبر `git` تبدیل کنی.

قوانین مهم:
- فقط و فقط یک شیء JSON معتبر برگردان. هیچ متن، توضیح یا بلوک کد اضافه‌ای ننویس.
- ساختار خروجی دقیقاً این باشد:
  {"command": "<دستور کامل git>", "explanation": "<توضیح کوتاه فارسی>"}
- مقدار command همیشه باید با کلمهٔ git شروع شود.
- explanation یک جملهٔ کوتاه فارسی دربارهٔ کاری که دستور انجام می‌دهد باشد.
- اگر درخواست مبهم بود، محتمل‌ترین دستور git را انتخاب کن.

نمونه‌ها:
کاربر: همه تغییرات را اضافه کن و با پیام «اصلاح باگ» کامیت کن
خروجی: {"command": "git add -A && git commit -m \\"اصلاح باگ\\"", "explanation": "همهٔ تغییرات را به استیج اضافه و با پیام داده‌شده کامیت می‌کند."}

کاربر: شاخه فعلی را روی origin پوش کن
خروجی: {"command": "git push origin HEAD", "explanation": "شاخهٔ فعلی را روی مخزن origin می‌فرستد."}

کاربر: یک شاخه جدید به اسم feature بساز و برو روی آن
خروجی: {"command": "git checkout -b feature", "explanation": "شاخهٔ جدید feature را می‌سازد و به آن سوییچ می‌کند."}

کاربر: وضعیت مخزن را نشانم بده
خروجی: {"command": "git status", "explanation": "وضعیت فعلی مخزن را نمایش می‌دهد."}

کاربر: سه کامیت آخر را ببینم
خروجی: {"command": "git log --oneline -3", "explanation": "سه کامیت آخر را به صورت خلاصه نشان می‌دهد."}
"""


# ---------------------------------------------------------------------------
# کمک‌تابع‌ها
# ---------------------------------------------------------------------------
def log_command(command: str) -> None:
    """هر دستور اجراشده را با تاریخ در git_ai.log ثبت می‌کند."""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{ts}] {command}\n")
    except Exception:
        # ثبت لاگ نباید جریان برنامه را متوقف کند.
        pass


def run_git_context_cmd(args: list) -> str:
    """یک دستور گیت را اجرا و خروجی متنی آن را برمی‌گرداند (برای جمع‌آوری context)."""
    try:
        out = subprocess.run(
            args, capture_output=True, text=True, timeout=15
        )
        return (out.stdout or "").strip()
    except Exception:
        return ""


def gather_repo_context() -> str:
    """شاخهٔ فعلی، وضعیت کوتاه و سه کامیت آخر را جمع می‌کند."""
    branch = run_git_context_cmd(["git", "branch", "--show-current"])
    status = run_git_context_cmd(["git", "status", "--short"])
    log = run_git_context_cmd(["git", "log", "--oneline", "-3"])

    parts = ["زمینهٔ مخزن فعلی:"]
    parts.append(f"شاخهٔ فعلی: {branch or '(نامشخص / خارج از مخزن گیت)'}")
    parts.append(f"وضعیت کوتاه:\n{status or '(بدون تغییر)'}")
    parts.append(f"سه کامیت آخر:\n{log or '(بدون کامیت)'}")
    return "\n".join(parts)


def extract_json(text: str) -> dict:
    """
    پارس مقاوم JSON: ابتدا کل متن، و اگر نشد اولین بلوک {...} را با regex استخراج می‌کند.
    """
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
def call_ollama(user_prompt: str, context: str) -> dict:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"{context}\n\nدرخواست کاربر: {user_prompt}"},
        ],
        "stream": False,
        "format": "json",
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    content = data.get("message", {}).get("content", "")
    return extract_json(content)


def call_openai(user_prompt: str, context: str) -> dict:
    if not LLM_API_KEY:
        raise RuntimeError(
            "کلید LLM_API_KEY تنظیم نشده است. آن را در فایل .env قرار دهید."
        )
    url = f"{LLM_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"{context}\n\nدرخواست کاربر: {user_prompt}"},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    return extract_json(content)


def ask_model(user_prompt: str) -> dict:
    """بر اساس PROVIDER مدل مناسب را صدا می‌زند و دیکشنری {command, explanation} برمی‌گرداند."""
    context = gather_repo_context()
    if PROVIDER == "openai":
        return call_openai(user_prompt, context)
    return call_ollama(user_prompt, context)


# ---------------------------------------------------------------------------
# ارزیابی ایمنی
# ---------------------------------------------------------------------------
def classify_command(command: str):
    """
    دستور را دسته‌بندی می‌کند.
    خروجی: یکی از 'blocked' | 'invalid' | 'dangerous' | 'safe' به همراه پیام.
    """
    cmd = (command or "").strip()

    if not cmd:
        return "invalid", "دستوری تولید نشد."

    # باید با git شروع شود.
    if not cmd.startswith("git"):
        return "invalid", "فقط دستورهایی که با git شروع می‌شوند اجرا می‌شوند."

    # لیست مسدود
    for pat in BLOCKED_PATTERNS:
        if re.search(pat, cmd):
            return "blocked", f"دستور مسدود است (الگوی خطرناک: {pat})."

    # لیست خطرناک
    for pat in DANGEROUS_PATTERNS:
        if re.search(pat, cmd):
            return "dangerous", f"این دستور برگشت‌ناپذیر یا پرخطر است (الگو: {pat})."

    return "safe", "امن"


# ---------------------------------------------------------------------------
# اجرای دستور
# ---------------------------------------------------------------------------
def execute_command(command: str) -> None:
    """دستور git را در شل اجرا و خروجی را چاپ می‌کند."""
    log_command(command)
    try:
        result = subprocess.run(command, shell=True, text=True)
        if result.returncode != 0:
            print(f"⚠️  دستور با کد خروج {result.returncode} پایان یافت.")
    except Exception as e:
        print(f"❌ خطا در اجرای دستور: {e}")


def confirm(prompt: str) -> bool:
    """تأیید y/n از کاربر."""
    try:
        ans = input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return ans in ("y", "yes", "بله", "آره")


def handle_request(user_prompt: str) -> None:
    """یک درخواست را پردازش می‌کند: مدل → ایمنی → اجرا."""
    try:
        result = ask_model(user_prompt)
    except requests.exceptions.ConnectionError:
        if PROVIDER == "openai":
            print(f"❌ اتصال به سرور برقرار نشد. base_url را بررسی کنید: {LLM_BASE_URL}")
        else:
            print(f"❌ اتصال به Ollama برقرار نشد. آیا Ollama روی {OLLAMA_URL} در حال اجراست؟")
        return
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response is not None else "?"
        if code in (401, 403):
            print("❌ کلید API نامعتبر است یا دسترسی ندارید (خطای احراز هویت).")
        else:
            print(f"❌ خطای سرور (کد {code}). دوباره تلاش کنید.")
        return
    except RuntimeError as e:
        print(f"❌ {e}")
        return
    except ValueError as e:
        print(f"❌ {e} پاسخ مدل قابل تبدیل به دستور نبود.")
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

    if kind == "invalid":
        print(f"⛔ اجرا نشد: {msg}")
        return
    if kind == "blocked":
        print(f"⛔ اجرا نشد: {msg}")
        return
    if kind == "dangerous":
        print(f"⚠️  هشدار: {msg}")
        if REQUIRE_CONFIRM_FOR_DANGEROUS:
            if not confirm("آیا مطمئن هستید؟ اجرا شود؟ (y/n): "):
                print("لغو شد.")
                return
        execute_command(command)
        return

    # safe
    print("✅ اجرا...")
    execute_command(command)


# ---------------------------------------------------------------------------
# حلقهٔ REPL
# ---------------------------------------------------------------------------
EXIT_WORDS = {"exit", "quit", "خروج", "q"}


def repl() -> None:
    print("=" * 60)
    print("  git-ai — دستیار گیت با هوش مصنوعی")
    print(f"  حالت: {PROVIDER}", end="")
    if PROVIDER == "openai":
        print(f"  |  مدل: {LLM_MODEL}  |  {LLM_BASE_URL}")
    else:
        print(f"  |  مدل: {OLLAMA_MODEL}  |  {OLLAMA_URL}")
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


def main() -> None:
    # اگر آرگومان داده شده باشد، یک‌باره اجرا می‌کنیم (حالت غیرتعاملی).
    if len(sys.argv) > 1:
        handle_request(" ".join(sys.argv[1:]))
        return
    repl()


if __name__ == "__main__":
    main()
