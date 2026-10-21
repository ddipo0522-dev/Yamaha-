#!/usr/bin/env bash
# restore-fusion.sh — Reproducible Fusion Factory restore for a new GitHub Codespace
#
# Usage:
#   curl -fsSL <this-script> | bash
#   # or run directly: bash restore-fusion.sh
#
# This script installs Fusion, registers the current repo as a Fusion project,
# and starts the dashboard. It does NOT contain any secrets. Provide your
# OpenRouter API key via the dashboard (Settings → Authentication → Custom
# Providers) before running AI tasks.
#
# Exit on error.
set -euo pipefail

echo "==> Fusion Factory restore starting"

# --- 1. Prerequisites -------------------------------------------------------
command -v node >/dev/null 2>&1 || { echo "ERROR: node not found"; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "ERROR: npm not found"; exit 1; }
command -v git >/dev/null 2>&1 || { echo "ERROR: git not found"; exit 1; }

NODE_VER=$(node -v | sed 's/v//')
echo "    node $NODE_VER  npm $(npm -v)"

# --- 2. Install Fusion CLI (version matching the previous environment) ------
echo "==> Installing @runfusion/fusion@0.77.0"
npm install -g @runfusion/fusion@0.77.0

command -v fn >/dev/null 2>&1 || { echo "ERROR: fn not on PATH after install"; exit 1; }
echo "    Fusion CLI: $(fn --version)"

# --- 3. Register current repo as a Fusion project ---------------------------
REPO_NAME="${FUSION_PROJECT_NAME:-$(basename "$PWD")}"
echo "==> Registering project '$REPO_NAME' in $PWD"

# Skip onboarding (non-interactive); providers configured via dashboard later.
FUSION_SKIP_ONBOARDING=1 fn init --name "$REPO_NAME"

echo "==> Project registered:"
fn project list

# --- 4. Start the dashboard -------------------------------------------------
echo "==> Starting Fusion dashboard on http://localhost:4040"
echo "    Run:  fn dashboard --no-auth   (then open the Codespaces port-4040 link)"
echo "    Note: Configure your OpenRouter API key in Settings → Authentication →"
echo "          Custom Providers (OpenAI-compatible, baseUrl https://openrouter.ai/api/v1)"
echo "          before creating AI tasks."
echo ""
echo "    To run headless instead:  fn serve --no-auth"

echo "==> Restore complete. Next: open dashboard, add OpenRouter key, create a task."
