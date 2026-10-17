// Che thong tin ca nhan cua hoc sinh truoc khi ghi nhat ky prompt (repo de cong khai).
// - Email that (tru @example.com cua bo kiem thu) -> "[email da che]"
// - Ten hoc sinh: liet ke moi ten mot dong trong prompt-log/.che_ten.txt (file nay khong len git)
const fs = require("fs");
const path = require("path");

const EMAIL = /[A-Za-z0-9._%+-]+@(?!example\.com\b)[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}/g;
const escape = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

function cheThongTin(text, root) {
  let out = String(text).replace(EMAIL, "[email da che]");
  const file = path.join(root, "prompt-log", ".che_ten.txt");
  if (fs.existsSync(file)) {
    for (const ten of fs.readFileSync(file, "utf8").split(/\r?\n/).map((s) => s.trim()).filter(Boolean)) {
      out = out.replace(new RegExp(escape(ten), "giu"), "[ten hoc sinh]");
    }
  }
  return out;
}

module.exports = { cheThongTin };
