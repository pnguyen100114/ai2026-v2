// Hook UserPromptSubmit cua Claude Code: ghi moi prompt vao prompt-log/PROMPT_LOG.md
// Claude Code gui JSON qua stdin: { session_id, prompt, cwd, ... }
const fs = require("fs");
const path = require("path");

let raw = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => (raw += chunk));
process.stdin.on("end", () => {
  try {
    const data = JSON.parse(raw || "{}");
    const prompt = (data.prompt || "").trim();
    if (!prompt) return;

    const root = process.env.CLAUDE_PROJECT_DIR || data.cwd || process.cwd();
    const dir = path.join(root, "prompt-log");
    const file = path.join(dir, "PROMPT_LOG.md");
    fs.mkdirSync(dir, { recursive: true });

    if (!fs.existsSync(file)) {
      fs.writeFileSync(
        file,
        "# Prompt Log\n\nNhat ky prompt da dung voi Claude Code trong qua trinh phat trien du an (ghi tu dong).\n\n"
      );
    }

    const time = new Date().toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh", hour12: false });
    const session = (data.session_id || "unknown").slice(0, 8);
    const entry = `---\n\n### ${time} · phien \`${session}\`\n\n${prompt}\n\n`;
    fs.appendFileSync(file, entry);
  } catch {
    // Khong bao gio chan prompt cua nguoi dung neu ghi log loi
  }
});
