#!/usr/bin/env python3
"""Export all Kilo sessions (chats) from kilo.db into readable Markdown + raw JSON.

Credentials found in tool output (GitHub tokens, provider API keys, ...) are
redacted before anything is written, because the export is meant to be
committed and published.
"""

import json
import os
import sqlite3
import datetime
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from redact import redact_obj, redact_text  # noqa: E402

DB = os.path.expanduser("~/.local/share/kilo/kilo.db")
OUT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/workspaces/Yamaha-/kilo-sessions")
OUT.mkdir(parents=True, exist_ok=True)

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
con.row_factory = sqlite3.Row


def ts(ms):
    if not ms:
        return ""
    return datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc).isoformat()


def jsonify(v, default=None):
    if v is None:
        return default
    try:
        return redact_obj(json.loads(v))
    except (TypeError, ValueError):
        return redact_text(v) if isinstance(v, str) else v


sessions = [dict(r) for r in con.execute("select * from session order by time_created")]
index = []

for s in sessions:
    sid = s["id"]
    slug = s["slug"] or sid
    msgs = [dict(r) for r in con.execute(
        "select * from message where session_id=? order by time_created", (sid,))]
    parts_by_msg = {}
    for r in con.execute(
            "select * from part where session_id=? order by time_created", (sid,)):
        d = dict(r)
        parts_by_msg.setdefault(d["message_id"], []).append(d)

    # ---- raw JSON export -------------------------------------------------
    raw = {
        "session": {k: (jsonify(v) if k in ("metadata", "model", "permission") else v)
                    for k, v in s.items()},
        "messages": [],
        "todos": [dict(t) for t in con.execute(
            "select * from todo where session_id=?", (sid,))],
    }
    for m in msgs:
        md = jsonify(m["data"], {}) or {}
        md["id"] = m["id"]
        md["session_id"] = m["session_id"]
        md["time_created"] = m["time_created"]
        md["parts"] = [jsonify(p["data"], {}) or {} for p in parts_by_msg.get(m["id"], [])]
        raw["messages"].append(md)

    base = f"{slug}-{sid}"
    (OUT / f"{base}.json").write_text(
        json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- Markdown transcript --------------------------------------------
    lines = []
    lines.append(f"# {redact_text(s['title'] or slug)}")
    lines.append("")
    lines.append(f"- Session ID: `{sid}`")
    lines.append(f"- Slug: `{slug}`")
    lines.append(f"- Project directory: `{s['directory']}`")
    lines.append(f"- Agent: `{s['agent']}`")
    lines.append(f"- Model: `{json.dumps(jsonify(s['model']), ensure_ascii=False)}`")
    lines.append(f"- Kilo version: `{s['version']}`")
    lines.append(f"- Created: {ts(s['time_created'])}")
    lines.append(f"- Last updated: {ts(s['time_updated'])}")
    lines.append(f"- Tokens in/out/reasoning: {s['tokens_input']}/{s['tokens_output']}/{s['tokens_reasoning']}")
    lines.append(f"- Files changed (summary): {s['summary_files']} (+{s['summary_additions']}/-{s['summary_deletions']})")
    lines.append("")

    for m in msgs:
        md = jsonify(m["data"], {}) or {}
        role = md.get("role", "unknown")
        role_ar = {"user": "المستخدم", "assistant": "المساعد"}.get(role, role)
        lines.append(f"## {role_ar} — {ts(m['time_created'])}")
        lines.append("")
        for p in parts_by_msg.get(m["id"], []):
            pd = jsonify(p["data"], {}) or {}
            ptype = pd.get("type")
            if ptype == "text":
                lines.append(pd.get("text", "").strip())
                lines.append("")
            elif ptype == "reasoning":
                lines.append("<details><summary>تفكير</summary>")
                lines.append("")
                lines.append(pd.get("text", "").strip())
                lines.append("")
                lines.append("</details>")
                lines.append("")
            elif ptype == "tool":
                st = pd.get("state") or {}
                inp = st.get("input") or {}
                name = pd.get("tool", "tool")
                cmd = inp.get("command") or inp.get("filePath") or inp.get("path") or ""
                lines.append(f"### 🔧 {name} `{st.get('status', '')}`")
                lines.append("")
                if cmd:
                    lines.append("```")
                    lines.append(str(cmd)[:4000])
                    lines.append("```")
                    lines.append("")
                out = st.get("output") or st.get("error") or ""
                if out:
                    lines.append("<details><summary>المخرجات</summary>")
                    lines.append("")
                    lines.append("```")
                    lines.append(str(out)[:4000])
                    lines.append("```")
                    lines.append("</details>")
                    lines.append("")
            elif ptype == "patch":
                lines.append(f"### 🩹 patch files: {', '.join(pd.get('files', []) or [])}")
                lines.append("")
        lines.append("")

    (OUT / f"{base}.md").write_text("\n".join(lines), encoding="utf-8")
    index.append({
        "id": sid, "slug": slug, "title": redact_text(s["title"] or ""),
        "created": ts(s["time_created"]), "updated": ts(s["time_updated"]),
        "messages": len(msgs), "files": f"{base}.md",
    })
    print(f"exported {sid} ({slug}) messages={len(msgs)}")

(OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

md = ["# Kilo Sessions Export", "",
      "تم تصدير كل جلسات Kilo (الدردشات) من قاعدة البيانات `~/.local/share/kilo/kilo.db`.", "",
      "لكل جلسة ملفان: ملف `.md` للقراءة، وملف `.json` بالبيانات الخام الكاملة.", "",
      "| Session ID | العنوان | الرسائل | created | updated | transcript |",
      "|---|---|---|---|---|---|"]
for i in index:
    md.append(f"| `{i['id']}` | {i['title']} | {i['messages']} | {i['created']} | {i['updated']} | [{i['files']}]({i['files']}) |")
(OUT / "README.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print("index written to", OUT)
