#!/usr/bin/env bash
# fusion-factory-maintenance.sh — Backup, restore, and recovery for Fusion Factory
#
# This script manages persistence of the Fusion Factory outside the Codespace lifecycle.
# It does NOT contain any secrets. The OpenRouter API key must be provided separately.
#
# Usage:
#   bash fusion-factory-maintenance.sh backup      # Create a verified backup
#   bash fusion-factory-maintenance.sh restore     # Restore from a backup
#   bash fusion-factory-maintenance.sh verify      # Verify backup integrity
#   bash fusion-factory-maintenance.sh status      # Show current factory state
#
# Non-negotiable: Never commit API keys, passwords, or secrets to Git.
set -euo pipefail

FUSION_HOME="$HOME/.fusion"
FUSION_WORKSPACE="/workspaces/Yamaha-/.fusion"
BACKUP_DIR="/tmp/kilo/backup"
BACKUP_ARCHIVE="$BACKUP_DIR/fusion-factory-backup.tar.gz"
GITHUB_REPO="ddipo0522-dev/Yamaha-"

echo "============================================================"
echo "  Fusion Factory Maintenance"
echo "============================================================"

cmd="${1:-status}"

case "$cmd" in
  status)
    echo ""
    echo "--- Fusion CLI ---"
    command -v fn >/dev/null 2>&1 && fn --version || echo "fn: NOT INSTALLED"
    echo ""
    echo "--- Fusion home ---"
    [ -d "$FUSION_HOME" ] && echo "$FUSION_HOME exists ($(du -sh "$FUSION_HOME" 2>/dev/null | cut -f1))" || echo "$FUSION_HOME: MISSING"
    echo ""
    echo "--- Embedded PostgreSQL ---"
    [ -d "$FUSION_HOME/embedded-postgres/default" ] && echo "PostgreSQL data dir exists" || echo "PostgreSQL data dir: MISSING"
    echo ""
    echo "--- Workspace .fusion ---"
    [ -d "$FUSION_WORKSPACE" ] && echo "$FUSION_WORKSPACE exists ($(du -sh "$FUSION_WORKSPACE" 2>/dev/null | cut -f1))" || echo "$FUSION_WORKSPACE: MISSING"
    echo ""
    echo "--- Running services ---"
    curl -s -m 5 http://localhost:4040/api/health 2>/dev/null | node -e 'let d="";process.stdin.on("data",c=>d+=c);process.stdin.on("end",()=>{try{const j=JSON.parse(d);console.log("Dashboard: OK (v"+j.version+", engine:"+(j.engine.available?"yes":"no")+", db:"+(j.database.healthy?"yes":"no")+")");}catch(e){console.log("Dashboard: NOT RESPONDING");}}) 2>/dev/null || echo "Dashboard: NOT RESPONDING"
    echo ""
    echo "--- Git state ---"
    cd /workspaces/Yahaha- 2>/dev/null || cd /workspaces/Yamaha-
    git status --short | head -5
    git log --oneline -1
    ;;

  backup)
    echo ""
    echo "--- Creating backup ---"
    mkdir -p "$BACKUP_DIR"
    TIMESTAMP=$(date +%Y%m%d-%H%M%S)
    ARCHIVE="$BACKUP_DIR/fusion-factory-backup-$TIMESTAMP.tar.gz"

    # Copy Fusion home with secrets redacted
    cp -r "$FUSION_HOME" "$BACKUP_DIR/fusion-home"
    node -e '
      const fs = require("fs");
      const p = process.env.HOME + "/.fusion/settings.json";
      const j = JSON.parse(fs.readFileSync(p, "utf8"));
      if (j.customProviders) {
        j.customProviders.forEach(cp => { if (cp.apiKey) cp.apiKey = "[REDACTED_FOR_BACKUP]"; });
      }
      fs.writeFileSync("'"$BACKUP_DIR"'/fusion-home/settings.json", JSON.stringify(j, null, 2) + "\n");
    '

    # Copy workspace .fusion
    cp -r "$FUSION_WORKSPACE" "$BACKUP_DIR/fusion-workspace"

    # Create checksums
    cd "$BACKUP_DIR"
    sha256sum fusion-home/settings.json > checksums.sha256
    find fusion-workspace -type f -exec sha256sum {} \; >> checksums.sha256

    # Create archive (includes PostgreSQL data - 73M binary)
    tar czf "$ARCHIVE" fusion-home/ fusion-workspace/ checksums.sha256
    rm -rf "$BACKUP_DIR/fusion-home" "$BACKUP_DIR/fusion-workspace"

    echo ""
    echo "Backup created: $ARCHIVE"
    echo "Size: $(du -h "$ARCHIVE" | cut -f1)"
    echo ""
    echo "IMPORTANT: This archive contains the OpenRouter API key (redacted)."
    echo "You must re-enter the OpenRouter API key after restore."
    echo "Store this archive outside the Codespace (download to your device)."
    ;;

  verify)
    echo ""
    echo "--- Verifying backup integrity ---"
    if [ ! -f "$BACKUP_ARCHIVE" ]; then
      echo "No backup archive found at $BACKUP_ARCHIVE"
      echo "Run 'backup' first."
      exit 1
    fi
    echo "Archive: $BACKUP_ARCHIVE ($(du -h "$BACKUP_ARCHIVE" | cut -f1))"
    tar tzf "$BACKUP_ARCHIVE" > /dev/null && echo "Archive integrity: OK" || echo "Archive integrity: FAILED"
    echo ""
    echo "--- Checking live factory ---"
    curl -s -m 5 http://localhost:4040/api/health 2>/dev/null | node -e 'let d="";process.stdin.on("data",c=>d+=c);process.stdin.on("end",()=>{try{const j=JSON.parse(d);console.log("Dashboard health: "+j.status);console.log("Engine: "+(j.engine.available?"available":"unavailable"));console.log("Database: "+(j.database.healthy?"healthy":"unhealthy")+" (corruption: "+(j.database.corruptionDetected?"yes":"no")+")");}catch(e){console.log("Dashboard: NOT RESPONDING");}}) 2>/dev/null || echo "Dashboard: NOT RESPONDING"
    ;;

  restore)
    echo ""
    echo "--- Restore procedure ---"
    echo "This restores the Fusion Factory configuration from backup."
    echo "The OpenRouter API key is REDACTED in backups and must be re-entered."
    echo ""
    if [ ! -f "$BACKUP_ARCHIVE" ]; then
      echo "No backup archive found at $BACKUP_ARCHIVE"
      echo "Place your backup archive at: $BACKUP_ARCHIVE"
      exit 1
    fi

    # Stop Fusion if running (safe - data is in PostgreSQL)
    if curl -s -m 5 http://localhost:4040/api/health >/dev/null 2>&1; then
      echo "Fusion is running. Stopping before restore..."
      pkill -f "fn dashboard" 2>/dev/null || true
      sleep 3
    fi

    # Extract backup
    cd "$BACKUP_DIR"
    tar xzf "$BACKUP_ARCHIVE"

    # Restore Fusion home (settings only - redacted, user must re-enter key)
    if [ -d "$BACKUP_DIR/fusion-home" ]; then
      rm -rf "$FUSION_HOME"
      cp -r "$BACKUP_DIR/fusion-home" "$FUSION_HOME"
      echo "Restored: $FUSION_HOME (settings redacted - re-enter OpenRouter key)"
    fi

    # Restore workspace .fusion
    if [ -d "$BACKUP_DIR/fusion-workspace" ]; then
      rm -rf "$FUSION_WORKSPACE"
      cp -r "$BACKUP_DIR/fusion-workspace" "$FUSION_WORKSPACE"
      echo "Restored: $FUSION_WORKSPACE"
    fi

    # Clean up extracted files
    rm -rf "$BACKUP_DIR/fusion-home" "$BACKUP_DIR/fusion-workspace"

    echo ""
    echo "Restore complete."
    echo "NEXT STEPS:"
    echo "  1. Re-enter OpenRouter API key via dashboard Settings → Custom Providers"
    echo "  2. Start Fusion: fn dashboard --no-auth"
    echo "  3. Verify: curl http://localhost:4040/api/health"
    ;;

  *)
    echo "Usage: $0 {backup|restore|verify|status}"
    exit 1
    ;;
esac
