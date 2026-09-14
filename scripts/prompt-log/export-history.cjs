// Xuat lich su prompt da dung voi AI (Claude Code + GitHub Copilot Chat) ra prompt-log/PROMPT_HISTORY.md
// Chay: node scripts/prompt-log/export-history.cjs [--with-replies]
const fs = require("fs");
const os = require("os");
const path = require("path");

const withReplies = process.argv.includes("--with-replies");
const root = path.resolve(__dirname, "..", "..");

const readJsonl = (file) =>
  fs.readFileSync(file, "utf8").split("\n").filter(Boolean).flatMap((line) => {
    try { return [JSON.parse(line)]; } catch { return []; }
  });

// ---------- Claude Code: ~/.claude/projects/<duong-dan-du-an-da-ma-hoa>/*.jsonl ----------
function claudeSessions() {
  const slug = root.replace(/[^A-Za-z0-9]/g, "-").toLowerCase();
  const projectsDir = path.join(os.homedir(), ".claude", "projects");
  if (!fs.existsSync(projectsDir)) return [];
  const dir = fs.readdirSync(projectsDir).find((d) => d.toLowerCase() === slug);
  if (!dir) return [];

  const textOf = (content) =>
    typeof content === "string"
      ? content
      : (content || [])
          .filter((b) => b.type === "text" && !b.text.trimStart().startsWith("<"))
          .map((b) => b.text)
          .join("\n");

  const sessions = [];
  for (const name of fs.readdirSync(path.join(projectsDir, dir)).filter((f) => f.endsWith(".jsonl"))) {
    const turns = [];
    for (const o of readJsonl(path.join(projectsDir, dir, name))) {
      if (o.isSidechain || o.isMeta) continue;
      if (o.type === "user" && !o.toolUseResult) {
        const text = textOf(o.message?.content).trim();
        if (text && !text.startsWith("<")) turns.push({ ts: Date.parse(o.timestamp), prompt: text, reply: "" });
      } else if (withReplies && o.type === "assistant" && turns.length) {
        const text = textOf(o.message?.content).trim();
        if (text) turns[turns.length - 1].reply = text;
      }
    }
    if (turns.length) sessions.push({ tool: "Claude Code", id: name.slice(0, 8), title: "", folder: root, turns });
  }
  return sessions;
}

// ---------- GitHub Copilot Chat: %APPDATA%/Code/User/workspaceStorage/<hash>/chatSessions/*.jsonl ----------
// File la nhat ky thay doi: kind 0 = trang thai ban dau, kind 2 voi k=["requests"] = them luot chat moi.
function copilotSessions() {
  const appData = process.env.APPDATA || path.join(os.homedir(), ".config");
  const sessions = [];
  for (const edition of ["Code", "Code - Insiders"]) {
    const ws = path.join(appData, edition, "User", "workspaceStorage");
    if (!fs.existsSync(ws)) continue;
    for (const hash of fs.readdirSync(ws)) {
      const wsJson = path.join(ws, hash, "workspace.json");
      const chatDir = path.join(ws, hash, "chatSessions");
      if (!fs.existsSync(wsJson) || !fs.existsSync(chatDir)) continue;

      let folder;
      try { folder = decodeURIComponent(JSON.parse(fs.readFileSync(wsJson, "utf8")).folder || ""); } catch { continue; }
      folder = folder.replace(/^file:\/\/\//, "");
      // Lay cac workspace thuoc bai du thi (thu muc co ten AI2026)
      if (!/ai\s?2026/i.test(folder)) continue;

      for (const name of fs.readdirSync(chatDir).filter((f) => /\.jsonl?$/.test(f))) {
        const log = readJsonl(path.join(chatDir, name));
        if (!log.length) continue;
        const state = log[0].v || log[0];
        const requests = [...(state.requests || [])];
        let title = state.customTitle || "";
        for (const o of log) {
          if (o.kind === 2 && o.k?.length === 1 && o.k[0] === "requests") requests.push(...o.v);
          if (o.kind === 1 && o.k?.[0] === "customTitle") title = o.v;
          // Cap nhat response cho --with-replies
          if (o.kind === 2 && o.k?.length === 3 && o.k[2] === "response" && requests[o.k[1]]) {
            requests[o.k[1]].response = [...(requests[o.k[1]].response || []), ...o.v];
          }
          if (o.kind === 1 && o.k?.length === 3 && o.k[2] === "response" && requests[o.k[1]]) {
            requests[o.k[1]].response = o.v;
          }
        }
        const turns = requests
          .map((r) => ({
            ts: r.timestamp,
            prompt: (r.message?.text || "").replace(/\r\n/g, "\n").trim(),
            reply: (r.response || [])
              .filter((p) => !p.kind && typeof p.value === "string")
              .map((p) => p.value)
              .join("")
              .trim(),
          }))
          .filter((t) => t.prompt);
        if (turns.length) sessions.push({ tool: "GitHub Copilot", id: name.slice(0, 8), title, folder, turns });
      }
    }
  }
  return sessions;
}

const sessions = [...claudeSessions(), ...copilotSessions()].sort((a, b) => a.turns[0].ts - b.turns[0].ts);

const fmt = (ts) => new Date(ts).toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh", hour12: false });
const total = sessions.reduce((n, s) => n + s.turns.length, 0);
const byTool = (tool) => sessions.filter((s) => s.tool === tool).reduce((n, s) => n + s.turns.length, 0);

let md = "# Prompt History\n\n";
md += "Toan bo prompt da dung voi cong cu AI trong qua trinh phat trien du an, trich tu lich su cua tung cong cu.\n\n";
md += `| Cong cu | So prompt |\n|---|---|\n| Claude Code | ${byTool("Claude Code")} |\n| GitHub Copilot | ${byTool("GitHub Copilot")} |\n| **Tong** | **${total}** |\n\n`;

let count = 0;
for (const s of sessions) {
  md += `## ${s.tool} · phien \`${s.id}\`${s.title ? ` — ${s.title}` : ""}\n\n`;
  md += `Bat dau: ${fmt(s.turns[0].ts)}`;
  if (path.resolve(s.folder).toLowerCase() !== root.toLowerCase()) md += ` · Thu muc: \`${s.folder}\``;
  md += "\n\n";
  for (const t of s.turns) {
    count++;
    md += `### ${count}. ${fmt(t.ts)}\n\n**Prompt:**\n\n${t.prompt}\n\n`;
    if (withReplies && t.reply) md += `**AI tra loi:**\n\n${t.reply}\n\n`;
  }
  md += "---\n\n";
}

const outDir = path.join(root, "prompt-log");
fs.mkdirSync(outDir, { recursive: true });
const out = path.join(outDir, "PROMPT_HISTORY.md");
fs.writeFileSync(out, md);
console.log(`Da xuat ${total} prompt (Claude Code: ${byTool("Claude Code")}, Copilot: ${byTool("GitHub Copilot")}) tu ${sessions.length} phien -> ${out}`);
