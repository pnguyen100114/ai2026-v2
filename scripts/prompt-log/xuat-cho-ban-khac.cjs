// Xuat PROMPT_LOG.md + PROMPT_HISTORY.md tren may cua mot thanh vien khac, cung dinh dang voi
// prompt-log/ cua du an. Chi can Node, khong can clone repo, khong ghi de file nao co san.
//
//   node xuat-cho-ban-khac.cjs --liet-ke        xem may nay co nhung du an/workspace nao, bao nhieu prompt
//   node xuat-cho-ban-khac.cjs                  xuat cac du an co ten khop ai2026 / mimo / gia su
//   node xuat-cho-ban-khac.cjs --loc "ten-thu-muc"   tu chon du an (regex, khong phan biet hoa thuong)
//
// Ket qua nam o thu muc prompt-log-xuat/ canh noi chay lenh.
const fs = require("fs");
const os = require("os");
const path = require("path");

const arg = (name) => {
  const i = process.argv.indexOf(name);
  return i > 0 ? process.argv[i + 1] : undefined;
};
const listOnly = process.argv.includes("--liet-ke");
const filter = new RegExp(arg("--loc") || "ai\\W?2026|mimo|gia\\W?su", "i");
const outDir = path.resolve(arg("--ra") || "prompt-log-xuat");

const readJsonl = (file) =>
  fs.readFileSync(file, "utf8").split("\n").filter(Boolean).flatMap((line) => {
    try { return [JSON.parse(line)]; } catch { return []; }
  });

// ---------- Claude Code: ~/.claude/projects/<duong-dan-du-an-da-ma-hoa>/*.jsonl ----------
const textOf = (content) =>
  typeof content === "string"
    ? content
    : (content || [])
        .filter((b) => b.type === "text" && !b.text.trimStart().startsWith("<"))
        .map((b) => b.text)
        .join("\n");

function claudeSessions() {
  const projectsDir = path.join(os.homedir(), ".claude", "projects");
  if (!fs.existsSync(projectsDir)) return [];
  const sessions = [];
  for (const dir of fs.readdirSync(projectsDir)) {
    const full = path.join(projectsDir, dir);
    if (!fs.statSync(full).isDirectory()) continue;
    for (const name of fs.readdirSync(full).filter((f) => f.endsWith(".jsonl"))) {
      const turns = [];
      let folder = dir;
      for (const o of readJsonl(path.join(full, name))) {
        if (o.cwd && folder === dir) folder = o.cwd;
        if (o.isSidechain || o.isMeta) continue;
        if (o.type === "user" && !o.toolUseResult) {
          const text = textOf(o.message?.content).trim();
          if (text && !text.startsWith("<")) turns.push({ ts: Date.parse(o.timestamp), prompt: text });
        }
      }
      if (turns.length) sessions.push({ tool: "Claude Code", id: name.slice(0, 8), title: "", folder, key: dir, turns });
    }
  }
  return sessions;
}

// ---------- GitHub Copilot Chat: <thu muc VS Code>/User/workspaceStorage/<hash>/chatSessions/*.jsonl ----------
function copilotSessions() {
  const bases = [
    process.env.APPDATA,                                               // Windows
    path.join(os.homedir(), "Library", "Application Support"),         // macOS
    path.join(os.homedir(), ".config"),                                // Linux
  ].filter(Boolean);
  const sessions = [];
  for (const base of bases) for (const edition of ["Code", "Code - Insiders", "Cursor"]) {
    const ws = path.join(base, edition, "User", "workspaceStorage");
    if (!fs.existsSync(ws)) continue;
    for (const hash of fs.readdirSync(ws)) {
      const wsJson = path.join(ws, hash, "workspace.json");
      const chatDir = path.join(ws, hash, "chatSessions");
      if (!fs.existsSync(wsJson) || !fs.existsSync(chatDir)) continue;
      let folder;
      try { folder = decodeURIComponent(JSON.parse(fs.readFileSync(wsJson, "utf8")).folder || ""); } catch { continue; }
      folder = folder.replace(/^file:\/\/\/?/, "");

      for (const name of fs.readdirSync(chatDir).filter((f) => /\.jsonl?$/.test(f))) {
        let log;
        try {
          log = name.endsWith(".jsonl") ? readJsonl(path.join(chatDir, name)) : [JSON.parse(fs.readFileSync(path.join(chatDir, name), "utf8"))];
        } catch { continue; }
        if (!log.length) continue;
        // .jsonl la nhat ky thay doi: kind 0 = trang thai dau, kind 2 voi k=["requests"] = them luot chat
        const state = log[0].v || log[0];
        const requests = [...(state.requests || [])];
        let title = state.customTitle || "";
        for (const o of log.slice(1)) {
          if (o.kind === 2 && o.k?.length === 1 && o.k[0] === "requests") requests.push(...o.v);
          if (o.kind === 1 && o.k?.[0] === "customTitle") title = o.v;
        }
        const turns = requests
          .map((r) => ({ ts: r.timestamp, prompt: (r.message?.text || "").replace(/\r\n/g, "\n").trim() }))
          .filter((t) => t.prompt && t.ts);
        if (turns.length) sessions.push({ tool: "GitHub Copilot", id: name.slice(0, 8), title, folder, key: folder, turns });
      }
    }
  }
  return sessions;
}

const all = [...claudeSessions(), ...copilotSessions()];

if (listOnly) {
  const groups = new Map();
  for (const s of all) {
    const k = `${s.tool} | ${s.folder}`;
    groups.set(k, (groups.get(k) || 0) + s.turns.length);
  }
  console.log("Cac du an co prompt tren may nay (dau * = se duoc xuat voi bo loc hien tai):\n");
  for (const [k, n] of [...groups].sort()) console.log(`${filter.test(k) ? "*" : " "} ${String(n).padStart(4)} prompt  ${k}`);
  console.log(`\nBo loc: /${filter.source}/i  — doi bang --loc "<mot phan ten thu muc>"`);
  process.exit(0);
}

const sessions = all
  .filter((s) => filter.test(s.folder) || filter.test(s.key))
  .sort((a, b) => a.turns[0].ts - b.turns[0].ts);
if (!sessions.length) {
  console.log(`Khong tim thay phien nao khop /${filter.source}/i. Chay voi --liet-ke de xem ten thu muc roi dung --loc.`);
  process.exit(1);
}

// ---------- Che thong tin ca nhan (giong scripts/prompt-log/che-thong-tin.cjs) ----------
const EMAIL = /[A-Za-z0-9._%+-]+@(?!example\.com\b)[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}/g;
const escape = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
// Script nay di le (gui cho ban khac) nen khong require che-thong-tin.cjs; tim .che_ten.txt canh script,
// noi chay lenh, hoac prompt-log/ cua repo khi chay tu scripts/prompt-log/.
const tenFile = [
  path.join(__dirname, ".che_ten.txt"),
  path.join(__dirname, "..", "..", "prompt-log", ".che_ten.txt"),
  path.resolve(".che_ten.txt"),
  path.resolve("prompt-log", ".che_ten.txt"),
].find(fs.existsSync);
const tenCanChe = tenFile ? fs.readFileSync(tenFile, "utf8").split(/\r?\n/).map((s) => s.trim()).filter(Boolean) : [];
const che = (text) => tenCanChe.reduce(
  (out, ten) => out.replace(new RegExp(escape(ten), "giu"), "[ten hoc sinh]"),
  String(text).replace(EMAIL, "[email da che]"),
);

// ---------- Ghi file, cung dinh dang voi prompt-log/ cua du an ----------
// Thu muc chinh = thu muc co nhieu phien Claude Code nhat; phien o thu muc khac thi ghi kem "Thu muc".
const tally = {};
for (const s of sessions) tally[s.folder] = (tally[s.folder] || 0) + 1;
const root = Object.keys(tally).sort((a, b) => tally[b] - tally[a])[0];
const same = (a, b) => path.resolve(a).toLowerCase() === path.resolve(b).toLowerCase();

const fmt = (ts) => new Date(ts).toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh", hour12: false });
const total = sessions.reduce((n, s) => n + s.turns.length, 0);
const byTool = (tool) => sessions.filter((s) => s.tool === tool).reduce((n, s) => n + s.turns.length, 0);

let history = "# Prompt History\n\n";
history += "Toan bo prompt da dung voi cong cu AI trong qua trinh phat trien du an, trich tu lich su cua tung cong cu.\n\n";
history += `| Cong cu | So prompt |\n|---|---|\n| Claude Code | ${byTool("Claude Code")} |\n| GitHub Copilot | ${byTool("GitHub Copilot")} |\n| **Tong** | **${total}** |\n\n`;
let count = 0;
for (const s of sessions) {
  history += `## ${s.tool} · phien \`${s.id}\`${s.title ? ` — ${s.title}` : ""}\n\n`;
  history += `Bat dau: ${fmt(s.turns[0].ts)}`;
  if (!same(s.folder, root)) history += ` · Thu muc: \`${s.folder.replace(/\\/g, "/")}\``;
  history += "\n\n";
  for (const t of s.turns) history += `### ${++count}. ${fmt(t.ts)}\n\n**Prompt:**\n\n${t.prompt}\n\n`;
  history += "---\n\n";
}

// PROMPT_LOG: tung prompt theo thu tu thoi gian, nhu hook log-prompt.cjs ghi
const onlyClaude = byTool("GitHub Copilot") === 0;
let log = "# Prompt Log\n\n";
log += `Nhat ky prompt da dung voi ${onlyClaude ? "Claude Code" : "Claude Code va GitHub Copilot"} trong qua trinh phat trien du an (ghi tu dong).\n\n`;
const entries = sessions.flatMap((s) => s.turns.map((t) => ({ ...t, id: s.id }))).sort((a, b) => a.ts - b.ts);
for (const e of entries) log += `---\n\n### ${fmt(e.ts)} · phien \`${e.id}\`\n\n${e.prompt}\n\n`;

fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, "PROMPT_HISTORY.md"), che(history));
fs.writeFileSync(path.join(outDir, "PROMPT_LOG.md"), che(log));
console.log(`Da xuat ${total} prompt (Claude Code: ${byTool("Claude Code")}, Copilot: ${byTool("GitHub Copilot")}) tu ${sessions.length} phien`);
console.log(`Thu muc chinh: ${root}${tenFile ? "" : "  (khong co .che_ten.txt: chi che email)"}`);
console.log(`-> ${path.join(outDir, "PROMPT_LOG.md")}\n-> ${path.join(outDir, "PROMPT_HISTORY.md")}`);
