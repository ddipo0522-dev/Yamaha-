#!/usr/bin/env bash
# Full environment backup: project repo + Kilo data + Fusion runtime state.
# Secrets (auth.json, ssh keys, *.key/*.pem) are excluded and every remaining
# text artifact is passed through the redactor before the archive is built.
set -euo pipefail

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
WORK="/tmp/kilo/backup-work"
OUTDIR="/tmp/kilo/backups"
NAME="yamaha-full-backup-${STAMP}"
DEST="${WORK}/${NAME}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

rm -rf "${WORK}"
mkdir -p "${DEST}" "${OUTDIR}"

echo "==> 1/7 project repo (incl. .git history)"
mkdir -p "${DEST}/project"
tar -C /workspaces/Yamaha- \
    --exclude='__pycache__' \
    --exclude='.pytest_cache' \
    --exclude='node_modules' \
    -cf - . | tar -C "${DEST}/project" -xf -

echo "==> 2/7 Kilo data (sessions db snapshot, storage, logs, snapshots)"
mkdir -p "${DEST}/kilo"
python3 - "$DEST" <<'PY'
import sqlite3, sys, os
dest = sys.argv[1]
src = os.path.expanduser("~/.local/share/kilo/kilo.db")
out = os.path.join(dest, "kilo", "kilo.db")
s = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
d = sqlite3.connect(out)
with d:
    s.backup(d)
d.close(); s.close()
print("kilo.db snapshot ->", out, os.path.getsize(out))
PY
for d in storage log snapshot; do
  [ -d "$HOME/.local/share/kilo/$d" ] && cp -a "$HOME/.local/share/kilo/$d" "${DEST}/kilo/" || true
done

echo "==> 3/7 Kilo global config"
mkdir -p "${DEST}/kilo/config"
cp -a "$HOME/.config/kilo" "${DEST}/kilo/config/" 2>/dev/null || true

echo "==> 4/7 Fusion factory state (project .fusion + global ~/.fusion, secrets excluded)"
mkdir -p "${DEST}/fusion"
cp -a /workspaces/Yamaha-/.fusion "${DEST}/fusion/project-fusion" 2>/dev/null || true
cp -a "$HOME/.fusion" "${DEST}/fusion/home-fusion" 2>/dev/null || true
find "${DEST}/fusion" -name "auth.json" -delete 2>/dev/null || true
find "${DEST}/fusion" -name "*.pem" -delete 2>/dev/null || true
find "${DEST}/fusion" -name "*.key" -delete 2>/dev/null || true
find "${DEST}/fusion" -name "postmaster.pid" -delete 2>/dev/null || true

echo "==> 5/7 redact credentials inside the kilo.db snapshot"
python3 - "${DEST}/kilo/kilo.db" "${SCRIPT_DIR}/redact.py" <<'PY'
import json, os, sqlite3, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[2])))
from redact import redact_text

db = sys.argv[1]
con = sqlite3.connect(db)
changed = 0
for table, column in (("message", "data"), ("part", "data"), ("session", "metadata"),
                       ("session", "permission"), ("session", "model"),
                       ("session", "title"), ("todo", "content")):
    try:
        rows = con.execute(f"select rowid, {column} from {table}").fetchall()
    except sqlite3.Error:
        continue
    for rowid, value in rows:
        if not isinstance(value, str):
            continue
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            cleaned = redact_text(value)
        else:
            def walk(node):
                if isinstance(node, str):
                    return redact_text(node)
                if isinstance(node, list):
                    return [walk(v) for v in node]
                if isinstance(node, dict):
                    return {k: walk(v) for k, v in node.items()}
                return node
            cleaned = json.dumps(walk(parsed), ensure_ascii=False)
            if not value.strip().startswith(("{", "[")):
                cleaned = redact_text(value)
        if cleaned != value:
            con.execute(f"update {table} set {column}=? where rowid=?", (cleaned, rowid))
            changed += 1
con.commit()
con.execute("vacuum")
con.close()
print(f"kilo.db redacted rows: {changed}")
PY

echo "==> 6/7 redact credentials in every text file of the archive"
find "${DEST}" -type f \
    -not -path "${DEST}/project/scripts/backup/*" \
    -print0 | xargs -0 python3 "${SCRIPT_DIR}/redact.py" | tail -5 || true

echo "==> 7/7 checksum + compress"
( cd "${DEST}" && find . -type f -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS.txt )
tar -czf "${OUTDIR}/${NAME}.tar.gz" -C "${WORK}" "${NAME}"
sha256sum "${OUTDIR}/${NAME}.tar.gz" > "${OUTDIR}/${NAME}.tar.gz.sha256"
du -sh "${OUTDIR}/${NAME}.tar.gz"
echo "BACKUP=${OUTDIR}/${NAME}.tar.gz"
