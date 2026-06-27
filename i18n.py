#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
git-ai — internationalization (i18n).

Supports English (en), Persian (fa), Arabic (ar), French (fr), Spanish (es).
Missing keys fall back to English, so the app always works.

Usage:
    import i18n
    i18n.set_language("fa")
    i18n.t("send")
    i18n.t("hdr_project", name="git-ai", branch="main")
"""

# (code, native name, RTL?)
LANGUAGES = [
    ("en", "English", False),
    ("fa", "فارسی", True),
    ("ar", "العربية", True),
    ("fr", "Français", False),
    ("es", "Español", False),
]
RTL = {"fa", "ar"}

_current = "en"


def available():
    return LANGUAGES


def get_language():
    return _current


def set_language(code):
    global _current
    code = (code or "en").lower()
    if code in TR:
        _current = code
    return _current


def is_rtl(code=None):
    return (code or _current) in RTL


def t(key, **kwargs):
    s = TR.get(_current, {}).get(key)
    if s is None:
        s = TR["en"].get(key, key)
    if kwargs:
        try:
            return s.format(**kwargs)
        except Exception:
            return s
    return s


def name_to_code(name):
    for code, native, _ in LANGUAGES:
        if native == name:
            return code
    return "en"


def code_to_name(code):
    for c, native, _ in LANGUAGES:
        if c == code:
            return native
    return "English"


# ---------------------------------------------------------------------------
# Translations
# ---------------------------------------------------------------------------
TR = {
    "en": {
        "subtitle": "chat with your repositories",
        "btn_settings": "⚙  Settings",
        "btn_about": "ⓘ  About",
        "btn_feedback": "💡  Feedback",
        "github_login": "GitHub: Login",
        "github_signed_in": "GitHub: {acct}",
        "language": "Language",
        "side_projects": "PROJECTS",
        "side_open": "📂  Open folder",
        "side_new": "✨  New project",
        "side_none": "No projects yet.\nOpen or create one below.",
        "tb_status": "Status", "tb_commit": "Commit", "tb_pull": "Pull",
        "tb_push": "Push", "tb_undo": "↩ Undo last",
        "try": "Try:",
        "chip_changed": "What changed?",
        "chip_commit": "Commit my changes",
        "chip_push": "Push to GitHub",
        "chip_newproj": "Create a new project",
        "chip_undo": "Undo my last commit",
        "send": "Send  ➤",
        "hdr_no_project": "No project selected",
        "hdr_project": "  📁 {name}     ⎇ {branch}",
        "no_branch": "no branch yet",
        "welcome": "👋 Hi! I'm your git assistant. Tell me what you want — e.g. "
                   "\"commit my changes\", \"create a new project called notes\", or "
                   "\"push to GitHub\". No git knowledge needed.",
        "pick_first": "First, let's pick a project to work on:",
        "pick_then_git": "Pick a project first, then I can run git for you:",
        "switched": "Switched to “{name}” (branch: {branch}).",
        "not_git_offer": "Switched to “{name}”. This folder isn't a git repo yet — "
                         "want me to set it up?",
        "btn_init": "Yes, initialize git",
        "removed": "Removed “{name}” from the list (the folder is untouched).",
        "ask_name": "Sure! What should the new project be called?",
        "ask_name2": "What should the new project be called?",
        "no_location": "No location chosen, so I didn't create it. Try again anytime.",
        "created": "✅ Created “{name}” and initialized git.",
        "first_commit_q": "Want me to make the first commit?",
        "btn_first_commit": "Yes, first commit",
        "which_project": "Which project?",
        "no_projects_actions": "You don't have any projects yet.",
        "greeting": "👋 Hey! I'm git-ai. Tell me what you'd like to do with your repository — "
                    "commit, push, pull, create a branch, start a new project, or undo a change.",
        "help": "I turn plain language into git actions. You can ask me to:\n"
                "• see what changed  • commit (I'll write the message)\n"
                "• push / pull  • create or switch projects\n"
                "• undo your last commit  • publish to GitHub\n\n"
                "Off-topic questions aren't my thing — I stick to git & GitHub.",
        "author_intro": "This project was created by Rick Sanchez (a vibe coder 😎). Links:",
        "more": "More:",
        "btn_star": "⭐ Star",
        "setup_nokey": "⚠️ You haven't entered a key yet, so the cloud AI isn't active.\n\n",
        "setup": "To use the cloud AI automatically, follow these steps:\n"
                 "1) Open “⚙ Settings” (top-right).\n"
                 "2) Click “Sign up & get a key” or visit:\n   {url}\n   Create a free account.\n"
                 "3) Copy your API key from the dashboard.\n"
                 "4) Back in Settings, paste it into “Bynara API key”, choose the "
                 "“Bynara / OpenAI-compatible” provider, optionally pick a model, and Save.\n\n"
                 "After that, just tell me what you want and I'll run git for you.\n"
                 "🔒 Prefer fully offline? Install Ollama and choose the Ollama provider.",
        "shortcuts": "Shortcuts:",
        "btn_signup": "Sign up & get a key",
        "btn_open_settings": "Open Settings",
        "btn_how": "How does this work?",
        "nokey_nudge": "To use the cloud AI, you'll need a free API key. I can walk you "
                       "through it — or set it up now:",
        "commit_drafted": "Here's a commit message I drafted:\n\n{msg}",
        "btn_commit_it": "✅ Commit it",
        "btn_commit_push": "🚀 Commit & push",
        "committed_push_q": "Committed! Want to upload it to GitHub now?",
        "btn_push_now": "🚀 Push to GitHub",
        "btn_not_now": "Not now",
        "dangerous_q": "This is irreversible:\n{cmd}\nRun it?",
        "btn_run_it": "Run it",
        "btn_cancel": "Cancel",
        "cancelled": "Okay, cancelled.",
        "blocked_unsafe": "🚫 I won't run that — it looks unsafe.\n{cmd}",
        "couldnt_form": "I couldn't form a safe git command for that. Could you rephrase? "
                        "For example: \"show what changed\" or \"commit everything\".",
        "model_unreachable": "⚠️ I couldn't reach the model: {msg}\n\nCheck Settings "
                             "(provider/key), or make sure Ollama is running.",
        "looking_changes": "Looking at your changes to write a commit message…",
        "open_first": "Open a project first.",
        "login_start": "Starting GitHub login — I'll show you a code to enter in your browser…",
        "login_need_gh": "To use GitHub I need the GitHub CLI (gh). Install it from "
                         "cli.github.com, then click GitHub again.",
        "already_signed": "You're already signed in to GitHub as {acct}.",
        "login_code": "🔑 Your one-time code is {code} (copied to clipboard). Enter it in the "
                      "browser window that just opened, then approve.",
        "star_invite": "If you find git-ai useful, I'd be thrilled if you ⭐ the project!",
        # feature requests
        "feature_btn": "💡  Request a feature",
        "feature_ask": "Sure — describe the feature or change you'd like. I'll send it to the "
                       "project as a GitHub issue.",
        "feature_confirm": "Send this as a feature request to the git-ai project?\n\n“{text}”",
        "btn_send_request": "Send request",
        "feature_done": "✅ Thanks! Your request was submitted:\n{url}",
        "feature_browser": "I couldn't post it via the GitHub CLI, so I opened a prefilled "
                           "issue page in your browser — just click “Submit new issue”.",
        # publish
        "publish_offer": "Want me to publish this project to GitHub? I'll handle the steps "
                         "(init, commit, create the repo, and push).",
        "btn_publish": "🚀 Publish to GitHub",
        "publishing": "Publishing to GitHub… this can take a few seconds.",
        "publish_need_gh": "Publishing needs the GitHub CLI (gh) and a login. Install gh from "
                           "cli.github.com and click GitHub to sign in, then try again.",
        "publish_done": "🎉 Done! Your project is now on GitHub:\n{url}",
        "no_remote_offer": "“{name}” isn't linked to GitHub yet. Want to publish it?",
        # settings
        "set_title": "Settings",
        "set_provider": "Provider",
        "set_ollama": "Ollama (local, offline)",
        "set_cloud": "Bynara / OpenAI-compatible (cloud)",
        "set_key": "Bynara API key",
        "set_show": "show",
        "set_base": "Base URL",
        "set_model": "Cloud model",
        "set_refresh": "Refresh",
        "set_ollama_model": "Ollama model",
        "set_explain": "Explain what each command did (plain language)",
        "set_save": "Save",
        "set_saved": "Settings saved. Using {provider} · {model}.",
        # about
        "about_subtitle": "An AI-powered git assistant",
        "about_stars": "⭐ {n} stars on GitHub",
        "about_star_btn": "⭐  Star this project on GitHub",
        "about_star_note": "If git-ai helps you, a star means a lot 💛",
        "about_created": "Created by",
        "about_tagline": "vibe coder",
        "about_close": "Close",
    },

    "fa": {
        "subtitle": "با مخزن‌هایت گفتگو کن",
        "btn_settings": "⚙  تنظیمات",
        "btn_about": "ⓘ  درباره",
        "btn_feedback": "💡  بازخورد",
        "github_login": "گیت‌هاب: ورود",
        "github_signed_in": "گیت‌هاب: {acct}",
        "language": "زبان",
        "side_projects": "پروژه‌ها",
        "side_open": "📂  باز کردن پوشه",
        "side_new": "✨  پروژهٔ جدید",
        "side_none": "هنوز پروژه‌ای نیست.\nیکی باز یا بساز.",
        "tb_status": "وضعیت", "tb_commit": "کامیت", "tb_pull": "پول",
        "tb_push": "پوش", "tb_undo": "↩ برگشت آخر",
        "try": "امتحان کن:",
        "chip_changed": "چی تغییر کرده؟",
        "chip_commit": "تغییراتم را کامیت کن",
        "chip_push": "پوش به گیت‌هاب",
        "chip_newproj": "یک پروژهٔ جدید بساز",
        "chip_undo": "آخرین کامیتم را برگردان",
        "send": "ارسال  ➤",
        "hdr_no_project": "پروژه‌ای انتخاب نشده",
        "hdr_project": "  📁 {name}     ⎇ {branch}",
        "no_branch": "هنوز شاخه‌ای نیست",
        "welcome": "👋 سلام! من دستیار گیت تو هستم. بگو چی می‌خوای — مثلاً «تغییراتم را کامیت کن»، "
                   "«یک پروژهٔ جدید به نام notes بساز» یا «پوش کن». نیازی نیست گیت بلد باشی.",
        "pick_first": "اول بیا یک پروژه برای کار انتخاب کنیم:",
        "pick_then_git": "اول یک پروژه انتخاب کن تا برات گیت اجرا کنم:",
        "switched": "رفتم روی «{name}» (شاخه: {branch}).",
        "not_git_offer": "رفتم روی «{name}». این پوشه هنوز مخزن گیت نیست — می‌خوای راه‌اندازی‌اش کنم؟",
        "btn_init": "بله، گیت را راه‌اندازی کن",
        "removed": "«{name}» از فهرست حذف شد (خود پوشه دست‌نخورده است).",
        "ask_name": "حتماً! اسم پروژهٔ جدید چی باشد؟",
        "ask_name2": "اسم پروژهٔ جدید چی باشد؟",
        "no_location": "محلی انتخاب نشد، پس نساختمش. هر وقت خواستی دوباره بگو.",
        "created": "✅ «{name}» ساخته و گیت راه‌اندازی شد.",
        "first_commit_q": "اولین کامیت را بزنم؟",
        "btn_first_commit": "بله، اولین کامیت",
        "which_project": "کدام پروژه؟",
        "no_projects_actions": "هنوز هیچ پروژه‌ای نداری.",
        "greeting": "👋 سلام! من git-ai هستم. بگو با مخزنت چی‌کار کنم — کامیت، پوش، پول، "
                    "ساخت شاخه، پروژهٔ جدید یا برگشت یک تغییر.",
        "help": "من زبان طبیعی را به دستورهای گیت تبدیل می‌کنم. می‌تونی بخوای:\n"
                "• ببینم چی تغییر کرده  • کامیت کنم (پیامش را خودم می‌نویسم)\n"
                "• پوش/پول  • پروژه بسازم یا سویچ کنم\n"
                "• آخرین کامیت را برگردانم  • روی گیت‌هاب منتشر کنم\n\n"
                "سوال‌های نامرتبط کار من نیست — فقط گیت و گیت‌هاب.",
        "author_intro": "این پروژه را «ریک سانچز» (یک وایب‌کدر 😎) ساخته. لینک‌ها:",
        "more": "بیشتر:",
        "btn_star": "⭐ ستاره بده",
        "setup_nokey": "⚠️ هنوز کلیدی وارد نکردی، پس هوش مصنوعی ابری فعال نیست.\n\n",
        "setup": "برای استفادهٔ خودکار از هوش مصنوعی ابری این مراحل را برو:\n"
                 "۱) از بالا-راست «⚙ تنظیمات» را باز کن.\n"
                 "۲) روی «ثبت‌نام و دریافت کلید» بزن یا برو به:\n   {url}\n   یک حساب رایگان بساز.\n"
                 "۳) کلید (API key) را از داشبورد کپی کن.\n"
                 "۴) برگرد در تنظیمات، کلید را در «Bynara API key» بگذار، حالت "
                 "«Bynara / OpenAI-compatible» را انتخاب کن، در صورت دلخواه یک مدل انتخاب کن و ذخیره بزن.\n\n"
                 "بعدش کافیه بگی چی می‌خوای تا برات گیت اجرا کنم.\n"
                 "🔒 ترجیح می‌دی کاملاً آفلاین باشه؟ Ollama را نصب و حالت Ollama را انتخاب کن.",
        "shortcuts": "میانبرها:",
        "btn_signup": "ثبت‌نام و دریافت کلید",
        "btn_open_settings": "باز کردن تنظیمات",
        "btn_how": "چطور کار می‌کند؟",
        "nokey_nudge": "برای استفاده از هوش مصنوعی ابری یک کلید رایگان لازم داری. می‌تونم راهنماییت کنم "
                       "یا همین حالا تنظیمش کنیم:",
        "commit_drafted": "این پیام کامیت را نوشتم:\n\n{msg}",
        "btn_commit_it": "✅ کامیت کن",
        "btn_commit_push": "🚀 کامیت و پوش",
        "committed_push_q": "کامیت شد! حالا روی گیت‌هاب آپلودش کنم؟",
        "btn_push_now": "🚀 پوش به گیت‌هاب",
        "btn_not_now": "الان نه",
        "dangerous_q": "این کار برگشت‌ناپذیر است:\n{cmd}\nاجرا شود؟",
        "btn_run_it": "اجرا کن",
        "btn_cancel": "لغو",
        "cancelled": "باشه، لغو شد.",
        "blocked_unsafe": "🚫 اجرا نمی‌کنم — ناامن به نظر می‌رسد.\n{cmd}",
        "couldnt_form": "نتونستم یک دستور گیت امن از این بسازم. می‌شه طور دیگه بگی؟ "
                        "مثلاً «چی تغییر کرده؟» یا «همه‌چی را کامیت کن».",
        "model_unreachable": "⚠️ نتونستم به مدل وصل شوم: {msg}\n\nتنظیمات (حالت/کلید) را بررسی کن "
                             "یا مطمئن شو Ollama در حال اجراست.",
        "looking_changes": "دارم تغییراتت را می‌بینم تا پیام کامیت بنویسم…",
        "open_first": "اول یک پروژه باز کن.",
        "login_start": "شروع ورود به گیت‌هاب — یک کد بهت می‌دهم که در مرورگر وارد کنی…",
        "login_need_gh": "برای گیت‌هاب به ابزار gh نیاز دارم. از cli.github.com نصبش کن و دوباره "
                         "روی گیت‌هاب بزن.",
        "already_signed": "همین حالا با حساب {acct} وارد گیت‌هاب هستی.",
        "login_code": "🔑 کد یک‌بارمصرفت {code} است (در کلیپ‌بورد کپی شد). در مرورگری که باز شد "
                      "واردش کن و تأیید کن.",
        "star_invite": "اگر git-ai برات مفید بود، خیلی خوشحال می‌شم به پروژه ⭐ بدی!",
        "feature_btn": "💡  درخواست قابلیت",
        "feature_ask": "حتماً — قابلیت یا تغییری که می‌خوای را توضیح بده. آن را به‌صورت یک issue "
                       "به پروژه می‌فرستم.",
        "feature_confirm": "این را به‌عنوان درخواست قابلیت به پروژهٔ git-ai بفرستم؟\n\n«{text}»",
        "btn_send_request": "ارسال درخواست",
        "feature_done": "✅ ممنون! درخواستت ثبت شد:\n{url}",
        "feature_browser": "نتونستم از طریق gh ثبتش کنم، پس صفحهٔ issue را با متن آماده در مرورگر "
                           "باز کردم — کافیه «Submit new issue» را بزنی.",
        "publish_offer": "می‌خوای این پروژه را روی گیت‌هاب منتشر کنم؟ همهٔ مراحل را خودم انجام می‌دهم "
                         "(init، کامیت، ساخت مخزن و پوش).",
        "btn_publish": "🚀 انتشار روی گیت‌هاب",
        "publishing": "در حال انتشار روی گیت‌هاب… چند ثانیه طول می‌کشد.",
        "publish_need_gh": "برای انتشار به gh و ورود نیاز است. gh را از cli.github.com نصب کن، روی "
                           "گیت‌هاب بزن تا وارد شوی، بعد دوباره امتحان کن.",
        "publish_done": "🎉 تمام! پروژه‌ات حالا روی گیت‌هاب است:\n{url}",
        "no_remote_offer": "«{name}» هنوز به گیت‌هاب وصل نیست. منتشرش کنم؟",
        "set_title": "تنظیمات",
        "set_provider": "ارائه‌دهنده",
        "set_ollama": "Ollama (محلی، آفلاین)",
        "set_cloud": "Bynara / سازگار با OpenAI (ابری)",
        "set_key": "کلید Bynara",
        "set_show": "نمایش",
        "set_base": "آدرس پایه (Base URL)",
        "set_model": "مدل ابری",
        "set_refresh": "به‌روزرسانی",
        "set_ollama_model": "مدل Ollama",
        "set_explain": "توضیح بده هر دستور چه کرد (به زبان ساده)",
        "set_save": "ذخیره",
        "set_saved": "تنظیمات ذخیره شد. استفاده از {provider} · {model}.",
        "about_subtitle": "دستیار گیت با هوش مصنوعی",
        "about_stars": "⭐ {n} ستاره در گیت‌هاب",
        "about_star_btn": "⭐  به این پروژه ستاره بده",
        "about_star_note": "اگر git-ai کمکت کرد، یک ستاره خیلی ارزش دارد 💛",
        "about_created": "ساختهٔ",
        "about_tagline": "وایب‌کدر",
        "about_close": "بستن",
    },

    "ar": {
        "subtitle": "تحدّث مع مستودعاتك",
        "btn_settings": "⚙  الإعدادات",
        "btn_about": "ⓘ  حول",
        "btn_feedback": "💡  ملاحظات",
        "github_login": "GitHub: تسجيل الدخول",
        "github_signed_in": "GitHub: {acct}",
        "language": "اللغة",
        "side_projects": "المشاريع",
        "side_open": "📂  فتح مجلد",
        "side_new": "✨  مشروع جديد",
        "side_none": "لا مشاريع بعد.\nافتح أو أنشئ واحدًا.",
        "tb_status": "الحالة", "tb_commit": "Commit", "tb_pull": "Pull",
        "tb_push": "Push", "tb_undo": "↩ تراجع",
        "try": "جرّب:",
        "chip_changed": "ما الذي تغيّر؟",
        "chip_commit": "احفظ تغييراتي",
        "chip_push": "ارفع إلى GitHub",
        "chip_newproj": "أنشئ مشروعًا جديدًا",
        "chip_undo": "تراجع عن آخر حفظ",
        "send": "إرسال  ➤",
        "hdr_no_project": "لا مشروع محدد",
        "hdr_project": "  📁 {name}     ⎇ {branch}",
        "no_branch": "لا فرع بعد",
        "welcome": "👋 مرحبًا! أنا مساعد git الخاص بك. قل لي ما تريد — مثل «احفظ تغييراتي» أو "
                   "«أنشئ مشروعًا باسم notes» أو «ارفع إلى GitHub». لا حاجة لمعرفة git.",
        "pick_first": "أولًا، لنختر مشروعًا للعمل عليه:",
        "pick_then_git": "اختر مشروعًا أولًا حتى أنفّذ git لك:",
        "switched": "انتقلت إلى «{name}» (الفرع: {branch}).",
        "not_git_offer": "انتقلت إلى «{name}». هذا المجلد ليس مستودع git بعد — أهيّئه لك؟",
        "btn_init": "نعم، هيّئ git",
        "removed": "تمت إزالة «{name}» من القائمة (المجلد لم يتغيّر).",
        "ask_name": "بالتأكيد! ما اسم المشروع الجديد؟",
        "ask_name2": "ما اسم المشروع الجديد؟",
        "no_location": "لم يتم اختيار مكان، لذلك لم أُنشئه. حاول مرة أخرى وقتما تشاء.",
        "created": "✅ تم إنشاء «{name}» وتهيئة git.",
        "first_commit_q": "أأقوم بأول حفظ (commit)؟",
        "btn_first_commit": "نعم، أول حفظ",
        "which_project": "أي مشروع؟",
        "no_projects_actions": "ليس لديك أي مشاريع بعد.",
        "greeting": "👋 مرحبًا! أنا git-ai. قل لي ماذا تريد أن تفعل بمستودعك — حفظ، رفع، سحب، "
                    "إنشاء فرع، مشروع جديد، أو التراجع عن تغيير.",
        "help": "أحوّل اللغة الطبيعية إلى أوامر git. يمكنك أن تطلب:\n"
                "• رؤية ما تغيّر  • الحفظ (سأكتب الرسالة)\n"
                "• الرفع / السحب  • إنشاء أو تبديل المشاريع\n"
                "• التراجع عن آخر حفظ  • النشر على GitHub\n\n"
                "الأسئلة خارج الموضوع ليست اختصاصي — أركّز على git و GitHub.",
        "author_intro": "أنشأ هذا المشروع ريك سانشيز (مبرمج 😎). الروابط:",
        "more": "المزيد:",
        "btn_star": "⭐ نجمة",
        "setup_nokey": "⚠️ لم تُدخل مفتاحًا بعد، لذا الذكاء الاصطناعي السحابي غير مُفعّل.\n\n",
        "setup": "لاستخدام الذكاء الاصطناعي السحابي تلقائيًا، اتبع الخطوات:\n"
                 "1) افتح «⚙ الإعدادات» (أعلى اليمين).\n"
                 "2) اضغط «سجّل واحصل على مفتاح» أو زر:\n   {url}\n   أنشئ حسابًا مجانيًا.\n"
                 "3) انسخ مفتاح الـ API من لوحة التحكم.\n"
                 "4) في الإعدادات، الصق المفتاح في «Bynara API key»، اختر مزوّد "
                 "«Bynara / OpenAI-compatible»، واختر نموذجًا ثم احفظ.\n\n"
                 "بعدها أخبرني بما تريد وسأنفّذ git لك.\n"
                 "🔒 تفضّل العمل دون اتصال؟ ثبّت Ollama واختر مزوّد Ollama.",
        "shortcuts": "اختصارات:",
        "btn_signup": "سجّل واحصل على مفتاح",
        "btn_open_settings": "افتح الإعدادات",
        "btn_how": "كيف يعمل هذا؟",
        "nokey_nudge": "لاستخدام الذكاء الاصطناعي السحابي تحتاج مفتاحًا مجانيًا. أرشدك أو نضبطه الآن:",
        "commit_drafted": "إليك رسالة الحفظ التي كتبتها:\n\n{msg}",
        "btn_commit_it": "✅ احفظ",
        "btn_commit_push": "🚀 احفظ وارفع",
        "committed_push_q": "تم الحفظ! أرفعه إلى GitHub الآن؟",
        "btn_push_now": "🚀 ارفع إلى GitHub",
        "btn_not_now": "ليس الآن",
        "dangerous_q": "هذا إجراء لا يمكن التراجع عنه:\n{cmd}\nأنفّذه؟",
        "btn_run_it": "نفّذ",
        "btn_cancel": "إلغاء",
        "cancelled": "حسنًا، تم الإلغاء.",
        "blocked_unsafe": "🚫 لن أنفّذ ذلك — يبدو غير آمن.\n{cmd}",
        "couldnt_form": "لم أستطع تكوين أمر git آمن. هل يمكنك إعادة الصياغة؟ "
                        "مثل «ماذا تغيّر؟» أو «احفظ كل شيء».",
        "model_unreachable": "⚠️ تعذّر الوصول إلى النموذج: {msg}\n\nتحقق من الإعدادات "
                             "(المزوّد/المفتاح) أو تأكد من تشغيل Ollama.",
        "looking_changes": "أراجع تغييراتك لكتابة رسالة الحفظ…",
        "open_first": "افتح مشروعًا أولًا.",
        "login_start": "بدء تسجيل الدخول إلى GitHub — سأعرض رمزًا تُدخله في المتصفح…",
        "login_need_gh": "أحتاج إلى GitHub CLI ‏(gh). ثبّته من cli.github.com ثم اضغط GitHub مجددًا.",
        "already_signed": "أنت مسجّل الدخول إلى GitHub باسم {acct}.",
        "login_code": "🔑 رمزك لمرة واحدة هو {code} (نُسخ إلى الحافظة). أدخله في نافذة المتصفح "
                      "التي فُتحت ثم وافق.",
        "star_invite": "إذا وجدت git-ai مفيدًا، سأكون سعيدًا جدًا لو منحت المشروع ⭐!",
        "feature_btn": "💡  طلب ميزة",
        "feature_ask": "بالتأكيد — صف الميزة أو التغيير الذي تريده. سأرسله إلى المشروع كـ issue.",
        "feature_confirm": "أأرسل هذا كطلب ميزة لمشروع git-ai؟\n\n«{text}»",
        "btn_send_request": "إرسال الطلب",
        "feature_done": "✅ شكرًا! تم إرسال طلبك:\n{url}",
        "feature_browser": "تعذّر النشر عبر gh، ففتحت صفحة issue مُعبّأة في متصفحك — فقط اضغط "
                           "«Submit new issue».",
        "publish_offer": "أتريدني أن أنشر هذا المشروع على GitHub؟ سأتولى الخطوات "
                         "(init، حفظ، إنشاء المستودع، ورفع).",
        "btn_publish": "🚀 انشر على GitHub",
        "publishing": "جارٍ النشر على GitHub… قد يستغرق بضع ثوانٍ.",
        "publish_need_gh": "النشر يحتاج إلى gh وتسجيل دخول. ثبّت gh من cli.github.com وسجّل الدخول ثم أعد المحاولة.",
        "publish_done": "🎉 تم! مشروعك الآن على GitHub:\n{url}",
        "no_remote_offer": "«{name}» غير مرتبط بـ GitHub بعد. أأنشره؟",
        "set_title": "الإعدادات",
        "set_provider": "المزوّد",
        "set_ollama": "Ollama (محلي، دون اتصال)",
        "set_cloud": "Bynara / متوافق مع OpenAI (سحابي)",
        "set_key": "مفتاح Bynara",
        "set_show": "إظهار",
        "set_base": "Base URL",
        "set_model": "النموذج السحابي",
        "set_refresh": "تحديث",
        "set_ollama_model": "نموذج Ollama",
        "set_explain": "اشرح ماذا فعل كل أمر (بلغة بسيطة)",
        "set_save": "حفظ",
        "set_saved": "تم حفظ الإعدادات. باستخدام {provider} · {model}.",
        "about_subtitle": "مساعد git مدعوم بالذكاء الاصطناعي",
        "about_stars": "⭐ {n} نجمة على GitHub",
        "about_star_btn": "⭐  امنح المشروع نجمة على GitHub",
        "about_star_note": "إذا ساعدك git-ai، فالنجمة تعني الكثير 💛",
        "about_created": "من إنشاء",
        "about_tagline": "vibe coder",
        "about_close": "إغلاق",
    },

    "fr": {
        "subtitle": "discutez avec vos dépôts",
        "btn_settings": "⚙  Réglages",
        "btn_about": "ⓘ  À propos",
        "btn_feedback": "💡  Retour",
        "github_login": "GitHub : Connexion",
        "github_signed_in": "GitHub : {acct}",
        "language": "Langue",
        "side_projects": "PROJETS",
        "side_open": "📂  Ouvrir un dossier",
        "side_new": "✨  Nouveau projet",
        "side_none": "Aucun projet.\nOuvrez-en ou créez-en un.",
        "tb_status": "Statut", "tb_commit": "Commit", "tb_pull": "Pull",
        "tb_push": "Push", "tb_undo": "↩ Annuler",
        "try": "Essayez :",
        "chip_changed": "Qu'est-ce qui a changé ?",
        "chip_commit": "Committer mes changements",
        "chip_push": "Pousser sur GitHub",
        "chip_newproj": "Créer un nouveau projet",
        "chip_undo": "Annuler mon dernier commit",
        "send": "Envoyer  ➤",
        "hdr_no_project": "Aucun projet sélectionné",
        "hdr_project": "  📁 {name}     ⎇ {branch}",
        "no_branch": "pas encore de branche",
        "welcome": "👋 Bonjour ! Je suis votre assistant git. Dites-moi ce que vous voulez — "
                   "p. ex. « committer mes changements », « créer un projet nommé notes » ou "
                   "« pousser sur GitHub ». Aucune connaissance de git requise.",
        "pick_first": "D'abord, choisissons un projet :",
        "pick_then_git": "Choisissez d'abord un projet pour que je lance git :",
        "switched": "Passé à « {name} » (branche : {branch}).",
        "not_git_offer": "Passé à « {name} ». Ce dossier n'est pas encore un dépôt git — "
                         "je le configure ?",
        "btn_init": "Oui, initialiser git",
        "removed": "« {name} » retiré de la liste (le dossier est intact).",
        "ask_name": "Bien sûr ! Quel nom pour le nouveau projet ?",
        "ask_name2": "Quel nom pour le nouveau projet ?",
        "no_location": "Aucun emplacement choisi, je ne l'ai pas créé. Réessayez quand vous voulez.",
        "created": "✅ « {name} » créé et git initialisé.",
        "first_commit_q": "Je fais le premier commit ?",
        "btn_first_commit": "Oui, premier commit",
        "which_project": "Quel projet ?",
        "no_projects_actions": "Vous n'avez encore aucun projet.",
        "greeting": "👋 Salut ! Je suis git-ai. Dites-moi quoi faire avec votre dépôt — "
                    "commit, push, pull, créer une branche, nouveau projet ou annuler un changement.",
        "help": "Je transforme le langage courant en actions git. Vous pouvez demander :\n"
                "• voir ce qui a changé  • committer (j'écris le message)\n"
                "• push / pull  • créer ou changer de projet\n"
                "• annuler le dernier commit  • publier sur GitHub\n\n"
                "Les questions hors sujet ne sont pas mon domaine — je me limite à git et GitHub.",
        "author_intro": "Ce projet a été créé par Rick Sanchez (un vibe coder 😎). Liens :",
        "more": "Plus :",
        "btn_star": "⭐ Star",
        "setup_nokey": "⚠️ Vous n'avez pas encore saisi de clé, l'IA cloud n'est donc pas active.\n\n",
        "setup": "Pour utiliser l'IA cloud automatiquement, suivez ces étapes :\n"
                 "1) Ouvrez « ⚙ Réglages » (en haut à droite).\n"
                 "2) Cliquez « S'inscrire et obtenir une clé » ou visitez :\n   {url}\n   Créez un compte gratuit.\n"
                 "3) Copiez votre clé API depuis le tableau de bord.\n"
                 "4) Dans Réglages, collez-la dans « Bynara API key », choisissez le fournisseur "
                 "« Bynara / OpenAI-compatible », choisissez un modèle puis Enregistrer.\n\n"
                 "Ensuite, dites-moi ce que vous voulez et je lance git.\n"
                 "🔒 Vous préférez hors ligne ? Installez Ollama et choisissez le fournisseur Ollama.",
        "shortcuts": "Raccourcis :",
        "btn_signup": "S'inscrire et obtenir une clé",
        "btn_open_settings": "Ouvrir les réglages",
        "btn_how": "Comment ça marche ?",
        "nokey_nudge": "Pour l'IA cloud, il faut une clé API gratuite. Je vous guide ou on la configure :",
        "commit_drafted": "Voici un message de commit que j'ai rédigé :\n\n{msg}",
        "btn_commit_it": "✅ Committer",
        "btn_commit_push": "🚀 Committer et pousser",
        "committed_push_q": "Committé ! Le pousser sur GitHub maintenant ?",
        "btn_push_now": "🚀 Pousser sur GitHub",
        "btn_not_now": "Pas maintenant",
        "dangerous_q": "Action irréversible :\n{cmd}\nL'exécuter ?",
        "btn_run_it": "Exécuter",
        "btn_cancel": "Annuler",
        "cancelled": "D'accord, annulé.",
        "blocked_unsafe": "🚫 Je ne l'exécuterai pas — cela semble dangereux.\n{cmd}",
        "couldnt_form": "Je n'ai pas pu former une commande git sûre. Pouvez-vous reformuler ? "
                        "P. ex. « montre ce qui a changé » ou « committe tout ».",
        "model_unreachable": "⚠️ Impossible de joindre le modèle : {msg}\n\nVérifiez les Réglages "
                             "(fournisseur/clé) ou que Ollama tourne.",
        "looking_changes": "J'examine vos changements pour écrire un message de commit…",
        "open_first": "Ouvrez d'abord un projet.",
        "login_start": "Connexion GitHub — je vais afficher un code à saisir dans le navigateur…",
        "login_need_gh": "GitHub nécessite GitHub CLI (gh). Installez-le depuis cli.github.com "
                         "puis recliquez sur GitHub.",
        "already_signed": "Vous êtes déjà connecté à GitHub en tant que {acct}.",
        "login_code": "🔑 Votre code à usage unique est {code} (copié). Saisissez-le dans la fenêtre "
                      "du navigateur ouverte, puis approuvez.",
        "star_invite": "Si git-ai vous est utile, je serais ravi que vous mettiez une ⭐ au projet !",
        "feature_btn": "💡  Demander une fonctionnalité",
        "feature_ask": "Bien sûr — décrivez la fonctionnalité ou le changement souhaité. "
                       "Je l'enverrai au projet comme une issue GitHub.",
        "feature_confirm": "Envoyer ceci comme demande de fonctionnalité au projet git-ai ?\n\n« {text} »",
        "btn_send_request": "Envoyer la demande",
        "feature_done": "✅ Merci ! Votre demande a été envoyée :\n{url}",
        "feature_browser": "Je n'ai pas pu publier via gh, j'ai donc ouvert une page d'issue "
                           "pré-remplie dans votre navigateur — cliquez « Submit new issue ».",
        "publish_offer": "Voulez-vous que je publie ce projet sur GitHub ? Je gère les étapes "
                         "(init, commit, création du dépôt et push).",
        "btn_publish": "🚀 Publier sur GitHub",
        "publishing": "Publication sur GitHub… cela peut prendre quelques secondes.",
        "publish_need_gh": "La publication nécessite gh et une connexion. Installez gh depuis "
                           "cli.github.com, connectez-vous, puis réessayez.",
        "publish_done": "🎉 Terminé ! Votre projet est sur GitHub :\n{url}",
        "no_remote_offer": "« {name} » n'est pas encore lié à GitHub. Le publier ?",
        "set_title": "Réglages",
        "set_provider": "Fournisseur",
        "set_ollama": "Ollama (local, hors ligne)",
        "set_cloud": "Bynara / compatible OpenAI (cloud)",
        "set_key": "Clé API Bynara",
        "set_show": "afficher",
        "set_base": "URL de base",
        "set_model": "Modèle cloud",
        "set_refresh": "Actualiser",
        "set_ollama_model": "Modèle Ollama",
        "set_explain": "Expliquer ce que chaque commande a fait (langage simple)",
        "set_save": "Enregistrer",
        "set_saved": "Réglages enregistrés. Utilisation de {provider} · {model}.",
        "about_subtitle": "Un assistant git propulsé par l'IA",
        "about_stars": "⭐ {n} étoiles sur GitHub",
        "about_star_btn": "⭐  Mettre une étoile sur GitHub",
        "about_star_note": "Si git-ai vous aide, une étoile compte beaucoup 💛",
        "about_created": "Créé par",
        "about_tagline": "vibe coder",
        "about_close": "Fermer",
    },

    "es": {
        "subtitle": "chatea con tus repositorios",
        "btn_settings": "⚙  Ajustes",
        "btn_about": "ⓘ  Acerca de",
        "btn_feedback": "💡  Sugerencias",
        "github_login": "GitHub: Iniciar sesión",
        "github_signed_in": "GitHub: {acct}",
        "language": "Idioma",
        "side_projects": "PROYECTOS",
        "side_open": "📂  Abrir carpeta",
        "side_new": "✨  Nuevo proyecto",
        "side_none": "Aún no hay proyectos.\nAbre o crea uno.",
        "tb_status": "Estado", "tb_commit": "Commit", "tb_pull": "Pull",
        "tb_push": "Push", "tb_undo": "↩ Deshacer",
        "try": "Prueba:",
        "chip_changed": "¿Qué cambió?",
        "chip_commit": "Haz commit de mis cambios",
        "chip_push": "Subir a GitHub",
        "chip_newproj": "Crear un proyecto nuevo",
        "chip_undo": "Deshacer mi último commit",
        "send": "Enviar  ➤",
        "hdr_no_project": "Ningún proyecto seleccionado",
        "hdr_project": "  📁 {name}     ⎇ {branch}",
        "no_branch": "sin rama todavía",
        "welcome": "👋 ¡Hola! Soy tu asistente de git. Dime qué quieres — p. ej. «haz commit de "
                   "mis cambios», «crea un proyecto llamado notes» o «sube a GitHub». No necesitas "
                   "saber git.",
        "pick_first": "Primero, elijamos un proyecto:",
        "pick_then_git": "Elige un proyecto primero y ejecutaré git por ti:",
        "switched": "Cambiado a «{name}» (rama: {branch}).",
        "not_git_offer": "Cambiado a «{name}». Esta carpeta aún no es un repo git — ¿lo configuro?",
        "btn_init": "Sí, inicializar git",
        "removed": "«{name}» eliminado de la lista (la carpeta queda intacta).",
        "ask_name": "¡Claro! ¿Cómo se llamará el nuevo proyecto?",
        "ask_name2": "¿Cómo se llamará el nuevo proyecto?",
        "no_location": "No se eligió ubicación, así que no lo creé. Inténtalo cuando quieras.",
        "created": "✅ «{name}» creado y git inicializado.",
        "first_commit_q": "¿Hago el primer commit?",
        "btn_first_commit": "Sí, primer commit",
        "which_project": "¿Qué proyecto?",
        "no_projects_actions": "Aún no tienes proyectos.",
        "greeting": "👋 ¡Hola! Soy git-ai. Dime qué hacer con tu repo — commit, push, pull, "
                    "crear una rama, nuevo proyecto o deshacer un cambio.",
        "help": "Convierto lenguaje natural en acciones de git. Puedes pedirme:\n"
                "• ver qué cambió  • hacer commit (yo escribo el mensaje)\n"
                "• push / pull  • crear o cambiar de proyecto\n"
                "• deshacer tu último commit  • publicar en GitHub\n\n"
                "Las preguntas fuera de tema no son lo mío — me centro en git y GitHub.",
        "author_intro": "Este proyecto fue creado por Rick Sanchez (un vibe coder 😎). Enlaces:",
        "more": "Más:",
        "btn_star": "⭐ Estrella",
        "setup_nokey": "⚠️ Aún no ingresaste una clave, así que la IA en la nube no está activa.\n\n",
        "setup": "Para usar la IA en la nube automáticamente, sigue estos pasos:\n"
                 "1) Abre «⚙ Ajustes» (arriba a la derecha).\n"
                 "2) Pulsa «Regístrate y obtén una clave» o visita:\n   {url}\n   Crea una cuenta gratis.\n"
                 "3) Copia tu clave API del panel.\n"
                 "4) En Ajustes, pégala en «Bynara API key», elige el proveedor "
                 "«Bynara / OpenAI-compatible», elige un modelo y Guarda.\n\n"
                 "Después dime qué quieres y ejecutaré git por ti.\n"
                 "🔒 ¿Prefieres sin conexión? Instala Ollama y elige el proveedor Ollama.",
        "shortcuts": "Atajos:",
        "btn_signup": "Regístrate y obtén una clave",
        "btn_open_settings": "Abrir Ajustes",
        "btn_how": "¿Cómo funciona esto?",
        "nokey_nudge": "Para la IA en la nube necesitas una clave API gratuita. Te guío o la configuramos ya:",
        "commit_drafted": "Aquí tienes un mensaje de commit que redacté:\n\n{msg}",
        "btn_commit_it": "✅ Hacer commit",
        "btn_commit_push": "🚀 Commit y push",
        "committed_push_q": "¡Commit hecho! ¿Lo subo a GitHub ahora?",
        "btn_push_now": "🚀 Subir a GitHub",
        "btn_not_now": "Ahora no",
        "dangerous_q": "Esto es irreversible:\n{cmd}\n¿Ejecutarlo?",
        "btn_run_it": "Ejecutar",
        "btn_cancel": "Cancelar",
        "cancelled": "Vale, cancelado.",
        "blocked_unsafe": "🚫 No ejecutaré eso — parece inseguro.\n{cmd}",
        "couldnt_form": "No pude formar un comando git seguro. ¿Puedes reformularlo? "
                        "P. ej. «muestra qué cambió» o «haz commit de todo».",
        "model_unreachable": "⚠️ No pude conectar con el modelo: {msg}\n\nRevisa Ajustes "
                             "(proveedor/clave) o asegúrate de que Ollama esté en marcha.",
        "looking_changes": "Revisando tus cambios para escribir un mensaje de commit…",
        "open_first": "Abre un proyecto primero.",
        "login_start": "Iniciando sesión en GitHub — te mostraré un código para el navegador…",
        "login_need_gh": "GitHub necesita GitHub CLI (gh). Instálalo desde cli.github.com y pulsa GitHub otra vez.",
        "already_signed": "Ya has iniciado sesión en GitHub como {acct}.",
        "login_code": "🔑 Tu código de un solo uso es {code} (copiado). Ingrésalo en la ventana del "
                      "navegador que se abrió y aprueba.",
        "star_invite": "Si git-ai te resulta útil, ¡me encantaría que le dieras una ⭐ al proyecto!",
        "feature_btn": "💡  Pedir una función",
        "feature_ask": "Claro — describe la función o el cambio que quieres. Lo enviaré al "
                       "proyecto como una issue de GitHub.",
        "feature_confirm": "¿Enviar esto como solicitud de función al proyecto git-ai?\n\n«{text}»",
        "btn_send_request": "Enviar solicitud",
        "feature_done": "✅ ¡Gracias! Tu solicitud fue enviada:\n{url}",
        "feature_browser": "No pude publicarla con gh, así que abrí una página de issue "
                           "rellenada en tu navegador — solo pulsa «Submit new issue».",
        "publish_offer": "¿Quieres que publique este proyecto en GitHub? Yo me encargo de los pasos "
                         "(init, commit, crear el repo y push).",
        "btn_publish": "🚀 Publicar en GitHub",
        "publishing": "Publicando en GitHub… puede tardar unos segundos.",
        "publish_need_gh": "Publicar necesita gh y sesión iniciada. Instala gh desde cli.github.com, "
                           "inicia sesión y vuelve a intentarlo.",
        "publish_done": "🎉 ¡Listo! Tu proyecto ya está en GitHub:\n{url}",
        "no_remote_offer": "«{name}» aún no está vinculado a GitHub. ¿Lo publico?",
        "set_title": "Ajustes",
        "set_provider": "Proveedor",
        "set_ollama": "Ollama (local, sin conexión)",
        "set_cloud": "Bynara / compatible con OpenAI (nube)",
        "set_key": "Clave API de Bynara",
        "set_show": "mostrar",
        "set_base": "URL base",
        "set_model": "Modelo en la nube",
        "set_refresh": "Actualizar",
        "set_ollama_model": "Modelo de Ollama",
        "set_explain": "Explicar qué hizo cada comando (lenguaje sencillo)",
        "set_save": "Guardar",
        "set_saved": "Ajustes guardados. Usando {provider} · {model}.",
        "about_subtitle": "Un asistente de git con IA",
        "about_stars": "⭐ {n} estrellas en GitHub",
        "about_star_btn": "⭐  Dale una estrella en GitHub",
        "about_star_note": "Si git-ai te ayuda, una estrella significa mucho 💛",
        "about_created": "Creado por",
        "about_tagline": "vibe coder",
        "about_close": "Cerrar",
    },
}
