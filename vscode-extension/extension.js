// git-ai — VS Code extension
// Chat with git in plain language. The AI turns your words into a single git
// command; safe ones run automatically, irreversible ones ask first.
// Mirrors the desktop app's logic (Ollama / OpenAI-compatible) with no deps.

const vscode = require("vscode");
const cp = require("child_process");
const http = require("http");
const https = require("https");
const { URL } = require("url");

const SIGNUP_URL = "https://router.bynara.id/register?ref=NMAP6F9D";

// --- safety rules (mirror of the Python core) ---------------------------
const BLOCKED = [
  /\brm\b/, /\bsudo\b/, /\bmkfs\b/, />\s*\/dev\//, />\s*\//,
  /:\(\)\s*\{/, /\bdd\b\s+if=/, /\bshutdown\b/, /\breboot\b/,
  /\$\(/, /`/, /\bcurl\b/, /\bwget\b/, /\bnc\b/, /\beval\b/, /\bcrontab\b/,
];
const DANGEROUS = [
  /reset\s+--hard/, /push\s+.*--force/, /push\s+.*\s-f\b/, /push\s+-f\b/,
  /clean\s+-[a-z]*f/, /branch\s+-D\b/, /checkout\s+--\s/, /\brestore\b/,
  /filter-branch/, /reflog\s+expire/, /gc\s+.*--prune/, /\brebase\b/,
  /stash\s+(drop|clear)/, /update-ref\s+-d/,
];
const READONLY = /^git\s+(status|log|diff|show|remote|branch(?!\s+-)|ls-files|ls-remote|rev-parse|config\s+--get)\b/i;

function classify(command) {
  const cmd = (command || "").trim();
  if (!cmd) return ["invalid", "No command was produced."];
  if (!cmd.startsWith("git")) return ["invalid", "Only git commands are allowed."];
  for (const p of BLOCKED) if (p.test(cmd)) return ["blocked", "Command blocked (unsafe)."];
  for (const p of DANGEROUS) if (p.test(cmd)) return ["dangerous", "This command is irreversible."];
  return ["safe", "safe"];
}

const SYSTEM_PROMPT = `You are a git command-line assistant.
Turn the user's plain-language request into a single, valid git command.
Return ONLY a JSON object: {"command":"<full git command>","explanation":"<short explanation>"}.
"command" must start with git. Reply in the user's language for the explanation.`;

const COMMIT_PROMPT = `You write git commit messages from a diff.
Return ONLY: {"title":"<short imperative subject>","description":"<optional body>"}.
Use Conventional Commits style.`;

const EXPLAIN_PROMPT = `You explain in simple, everyday language what a git command just did,
given the command and its output. 1-2 short non-technical sentences.
Return ONLY: {"reply":"<explanation>"}.`;

// --- shell helpers -------------------------------------------------------
function cwd() {
  const f = vscode.workspace.workspaceFolders;
  return f && f.length ? f[0].uri.fsPath : null;
}

function sh(command, dir) {
  return new Promise((resolve) => {
    cp.exec(command, { cwd: dir, maxBuffer: 10 * 1024 * 1024 }, (err, so, se) => {
      let out = (so || "") + (se || "");
      if (err && err.code) out += `\nExit code: ${err.code}`;
      resolve(out.trim() || "(no output)");
    });
  });
}

function shOut(command, dir) {
  return new Promise((resolve) => {
    cp.exec(command, { cwd: dir, maxBuffer: 10 * 1024 * 1024 }, (e, so) => resolve((so || "").trim()));
  });
}

async function gatherContext(dir) {
  const branch = await shOut("git branch --show-current", dir);
  const status = await shOut("git status --short", dir);
  const log = await shOut("git log --oneline -3", dir);
  return `Current repository context:\nCurrent branch: ${branch || "(unknown)"}\n` +
         `Short status:\n${status || "(no changes)"}\nLast 3 commits:\n${log || "(no commits)"}`;
}

// --- JSON parsing (tolerant) --------------------------------------------
function extractJson(text) {
  let s = (text || "").trim().replace(/^```[a-zA-Z]*\s*/, "").replace(/\s*```$/, "").trim();
  const tries = [s];
  const m = s.match(/\{[\s\S]*\}/);
  if (m) tries.push(m[0]);
  for (const c of tries) {
    for (const v of [c, c.replace(/,(\s*[}\]])/g, "$1")]) {
      try { return JSON.parse(v); } catch (e) { /* keep trying */ }
    }
  }
  throw new Error("The model did not return valid JSON.");
}

// --- HTTP ----------------------------------------------------------------
function httpJson(urlStr, { method = "POST", headers = {}, body } = {}) {
  return new Promise((resolve, reject) => {
    let u;
    try { u = new URL(urlStr); } catch (e) { return reject(e); }
    const lib = u.protocol === "https:" ? https : http;
    const data = body ? JSON.stringify(body) : null;
    const req = lib.request(u, {
      method,
      headers: { "Content-Type": "application/json", ...headers,
                 ...(data ? { "Content-Length": Buffer.byteLength(data) } : {}) },
      timeout: 120000,
    }, (res) => {
      let chunks = "";
      res.on("data", (d) => (chunks += d));
      res.on("end", () => {
        if (res.statusCode >= 400) return reject(new Error(`HTTP ${res.statusCode}: ${chunks.slice(0, 200)}`));
        try { resolve(JSON.parse(chunks)); } catch (e) { reject(e); }
      });
    });
    req.on("error", reject);
    req.on("timeout", () => req.destroy(new Error("request timed out")));
    if (data) req.write(data);
    req.end();
  });
}

async function callModel(system, user) {
  const cfg = vscode.workspace.getConfiguration("gitAi");
  const provider = cfg.get("provider");
  if (provider === "openai") {
    const key = cfg.get("apiKey");
    if (!key) throw new Error("No API key set. Open Settings → git-ai, or get a free key.");
    const base = (cfg.get("baseUrl") || "").replace(/\/$/, "");
    const j = await httpJson(`${base}/chat/completions`, {
      headers: { Authorization: `Bearer ${key}` },
      body: { model: cfg.get("model"), temperature: 0,
              response_format: { type: "json_object" },
              messages: [{ role: "system", content: system }, { role: "user", content: user }] },
    });
    return extractJson(j.choices[0].message.content);
  }
  const j = await httpJson(cfg.get("ollamaUrl"), {
    body: { model: cfg.get("ollamaModel"), stream: false, format: "json",
            messages: [{ role: "system", content: system }, { role: "user", content: user }] },
  });
  return extractJson((j.message && j.message.content) || "");
}

async function askGit(text, dir) {
  const ctx = await gatherContext(dir);
  return callModel(SYSTEM_PROMPT, `${ctx}\n\nUser request: ${text}`);
}

async function genCommit(dir) {
  let diff = await shOut("git diff --staged", dir);
  if (!diff) diff = await shOut("git diff", dir);
  const status = await shOut("git status --short", dir);
  if (!diff && !status) throw new Error("No changes found to commit.");
  const r = await callModel(COMMIT_PROMPT, `Status:\n${status}\n\nDiff:\n${diff.slice(0, 6000)}`);
  return { title: (r.title || "").trim(), description: (r.description || "").trim() };
}

async function explain(command, out) {
  try {
    const r = await callModel(EXPLAIN_PROMPT, `Command: ${command}\n\nOutput:\n${(out || "").slice(0, 1500)}`);
    return (r.reply || "").trim();
  } catch (e) { return ""; }
}

// --- webview chat provider ----------------------------------------------
class ChatProvider {
  constructor(ctx) { this.ctx = ctx; }

  resolveWebviewView(view) {
    this.view = view;
    view.webview.options = { enableScripts: true };
    view.webview.html = getHtml();
    view.webview.onDidReceiveMessage((msg) => this.onMessage(msg));
  }

  post(m) { if (this.view) this.view.webview.postMessage(m); }
  bot(text) { this.post({ type: "bot", text }); }
  term(text) { this.post({ type: "term", text }); }

  async onMessage(msg) {
    const dir = cwd();
    if (msg.type === "send") {
      if (!dir) return this.bot("Open a folder in VS Code first, then I can run git for you.");
      this.post({ type: "user", text: msg.text });
      this.post({ type: "typing" });
      try {
        const r = await askGit(msg.text, dir);
        this.post({ type: "stopTyping" });
        await this.handleCommand(r.command, r.explanation, dir);
      } catch (e) {
        this.post({ type: "stopTyping" });
        this.bot("⚠️ " + e.message);
      }
    } else if (msg.type === "action") {
      if (!dir) return this.bot("Open a folder in VS Code first.");
      if (msg.action === "status") return this.run("git status", dir);
      if (msg.action === "pull") return this.run("git pull", dir);
      if (msg.action === "push") {
        const b = (await shOut("git branch --show-current", dir)) || "HEAD";
        return this.run(`git push -u origin ${b}`, dir);
      }
      if (msg.action === "commit") return this.smartCommit(dir);
    } else if (msg.type === "confirm") {
      if (msg.approve) await this.run(msg.command, dir, true);
      else this.bot("Okay, cancelled.");
    } else if (msg.type === "signup") {
      vscode.env.openExternal(vscode.Uri.parse(SIGNUP_URL));
    }
  }

  async handleCommand(command, explanation, dir) {
    const [kind, why] = classify(command);
    if (kind === "invalid") return this.bot("I couldn't turn that into a git action. Try rephrasing.");
    if (kind === "blocked") return this.bot("🚫 I won't run that — it looks unsafe.\n" + command);
    if (explanation) this.bot(explanation);
    if (kind === "dangerous") {
      const confirm = vscode.workspace.getConfiguration("gitAi").get("confirmDangerous");
      if (confirm) return this.post({ type: "confirm", command, why });
    }
    await this.run(command, dir);
  }

  async run(command, dir, dangerousOk) {
    const out = await sh(command, dir);
    this.term(`$ ${command}\n${out}`);
    if (!READONLY.test(command.trim())) {
      const e = await explain(command, out);
      if (e) this.bot(e);
    }
    if (/commit/.test(command) && !/push/.test(command)) {
      this.post({ type: "offerPush" });
    }
  }

  async smartCommit(dir) {
    this.post({ type: "typing" });
    try {
      const m = await genCommit(dir);
      this.post({ type: "stopTyping" });
      const esc = (s) => s.replace(/"/g, '\\"');
      let cmd = `git add -A && git commit -m "${esc(m.title)}"`;
      if (m.description) cmd += ` -m "${esc(m.description)}"`;
      this.post({ type: "commitDraft", preview: m.title + (m.description ? "\n\n" + m.description : ""), command: cmd });
    } catch (e) {
      this.post({ type: "stopTyping" });
      this.bot("⚠️ " + e.message);
    }
  }
}

function getHtml() {
  return `<!DOCTYPE html><html><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline';">
<style>
  body{font-family:var(--vscode-font-family);color:var(--vscode-foreground);margin:0;padding:0;display:flex;flex-direction:column;height:100vh}
  #log{flex:1;overflow-y:auto;padding:10px}
  .row{display:flex;margin:6px 0}
  .me{justify-content:flex-end}
  .bubble{max-width:85%;padding:8px 11px;border-radius:10px;white-space:pre-wrap;line-height:1.45;font-size:13px}
  .bot{background:var(--vscode-editorWidget-background);border:1px solid var(--vscode-widget-border)}
  .usr{background:var(--vscode-button-background);color:var(--vscode-button-foreground)}
  .term{background:#0d1117;color:#7ee787;font-family:var(--vscode-editor-font-family,monospace);font-size:12px}
  .muted{opacity:.6;font-size:11px;margin:0 4px 2px}
  .acts{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px}
  button{background:var(--vscode-button-background);color:var(--vscode-button-foreground);border:none;border-radius:6px;padding:5px 10px;cursor:pointer;font-size:12px}
  button.sec{background:var(--vscode-button-secondaryBackground);color:var(--vscode-button-secondaryForeground)}
  #bar{display:flex;gap:6px;flex-wrap:wrap;padding:6px 10px;border-top:1px solid var(--vscode-widget-border)}
  #bar button{background:var(--vscode-editorWidget-background);color:var(--vscode-foreground)}
  #inwrap{display:flex;gap:6px;padding:8px 10px;border-top:1px solid var(--vscode-widget-border)}
  #in{flex:1;background:var(--vscode-input-background);color:var(--vscode-input-foreground);border:1px solid var(--vscode-input-border,transparent);border-radius:6px;padding:7px}
</style></head><body>
<div id="log"></div>
<div id="bar">
  <button onclick="act('status')">Status</button>
  <button onclick="act('commit')">Commit</button>
  <button onclick="act('pull')">Pull</button>
  <button onclick="act('push')">Push</button>
</div>
<div id="inwrap">
  <input id="in" placeholder="Tell me what to do… (e.g. commit my changes)"/>
  <button onclick="send()">Send</button>
</div>
<script>
  const vs = acquireVsCodeApi();
  const log = document.getElementById('log'), input = document.getElementById('in');
  let typing = null;
  function add(text, cls, sender){
    const row = document.createElement('div'); row.className = 'row' + (cls==='usr'?' me':'');
    const col = document.createElement('div');
    if(sender){ const s=document.createElement('div'); s.className='muted'; s.textContent=sender; col.appendChild(s);}
    const b = document.createElement('div'); b.className = 'bubble ' + cls; b.textContent = text; col.appendChild(b);
    row.appendChild(col); log.appendChild(row); log.scrollTop = log.scrollHeight; return col;
  }
  function send(){ const t=input.value.trim(); if(!t)return; input.value=''; vs.postMessage({type:'send',text:t}); }
  function act(a){ vs.postMessage({type:'action',action:a}); }
  input.addEventListener('keydown',e=>{ if(e.key==='Enter') send(); });
  window.addEventListener('message', ev=>{
    const m = ev.data;
    if(m.type==='user') add(m.text,'usr','You');
    else if(m.type==='bot') add(m.text,'bot','git-ai');
    else if(m.type==='term') add(m.text,'term','git-ai · output');
    else if(m.type==='typing'){ typing = add('● ● ●','bot','git-ai'); }
    else if(m.type==='stopTyping'){ if(typing){ typing.parentElement.remove(); typing=null; } }
    else if(m.type==='confirm'){
      const col = add(m.why + '\\n' + m.command + '\\nRun it?','bot','git-ai');
      const acts = document.createElement('div'); acts.className='acts';
      const yes=document.createElement('button'); yes.textContent='Run it';
      yes.onclick=()=>{acts.remove(); vs.postMessage({type:'confirm',approve:true,command:m.command});};
      const no=document.createElement('button'); no.className='sec'; no.textContent='Cancel';
      no.onclick=()=>{acts.remove(); vs.postMessage({type:'confirm',approve:false});};
      acts.appendChild(yes); acts.appendChild(no); col.appendChild(acts);
    }
    else if(m.type==='commitDraft'){
      const col = add('Here is a commit message I drafted:\\n\\n'+m.preview,'bot','git-ai');
      const acts=document.createElement('div'); acts.className='acts';
      const c=document.createElement('button'); c.textContent='✅ Commit';
      c.onclick=()=>{acts.remove(); vs.postMessage({type:'confirm',approve:true,command:m.command});};
      acts.appendChild(c); col.appendChild(acts);
    }
    else if(m.type==='offerPush'){
      const col = add('Committed! Push to GitHub now?','bot','git-ai');
      const acts=document.createElement('div'); acts.className='acts';
      const p=document.createElement('button'); p.textContent='🚀 Push';
      p.onclick=()=>{acts.remove(); vs.postMessage({type:'action',action:'push'});};
      acts.appendChild(p); col.appendChild(acts);
    }
  });
  add("👋 Hi! I'm git-ai. Tell me what to do with your repo — commit, push, pull, or anything else. No git knowledge needed.","bot","git-ai");
</script></body></html>`;
}

function activate(context) {
  const provider = new ChatProvider(context);
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider("gitAiChat", provider),
    vscode.commands.registerCommand("gitAi.openChat", () => {
      vscode.commands.executeCommand("workbench.view.extension.gitAi");
    })
  );
}

function deactivate() {}

module.exports = { activate, deactivate };
