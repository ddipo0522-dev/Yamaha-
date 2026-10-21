# Fusion Factory Deployment Guide (Ubuntu Server)

This guide is for deploying the Fusion factory (Runfusion v0.77.0) on a fresh Ubuntu server. 
This repository (`ddipo0522-dev/Yamaha-`) contains the workspace/project files; the Fusion CLI is installed globally via npm.

> **Important**: The backup file from this Codespace (`/tmp/kilo/backup/fusion-factory-backup.tar.gz`) was NOT found in the filesystem check. If you have it downloaded externally, use it for restoration.

## Prerequisites

- Ubuntu 22.04/24.04 LTS
- Node.js 24.x (matching the version used in this Codespace)
- npm
- systemd
- A dedicated user (e.g., `ubuntu`)

## Installation

### 1. Install Node.js
```bash
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### 2. Install Fusion CLI
```bash
npm config set prefix ~/.npm-global
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
npm install -g @runfusion/fusion@0.77.0
fn --version
```

### 3. Clone the repository
```bash
git clone https://github.com/ddipo0522-dev/Yamaha-.git
cd Yamaha-
```

### 4. Install cloudflared (for tunnel)
```bash
curl -L https://pkg.cloudflare.com/cloudflared.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloudflared.gpg
echo "deb [signed-by=/usr/share/keyrings/cloudflared.gpg] https://pkg.cloudflare.com/cloudflared $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt update && sudo apt install cloudflared
```

### 5. Configure environment
Fusion v0.77.0 does **not** auto-load `.env` files. Configuration is stored in `~/.fusion/settings.json`.
Copy the example env file for reference:
```bash
cp deploy/examples/.env.example .env
chmod 600 .env
```

To configure the OpenRouter provider, you must edit `~/.fusion/settings.json` with the correct structure (see the example in this repo's factory-config/ or use the Fusion UI after first start).

### 6. Set up Fusion

**For a fresh installation (new factory):**
```bash
fn init --name Yamaha-
# Configure provider via Fusion dashboard/UI after starting
```

**For restoring an existing factory (with data):**
If you have a backup from the previous environment, restore:
- `~/.fusion/` (global settings, embedded PostgreSQL data)
- `<repo>/.fusion/` (project state, tasks)
```bash
# Extract backup to correct locations
tar xzf fusion-factory-backup.tar.gz
# Copy contents to appropriate locations
# Re-enter API keys manually (they are redacted in backups)
```

### 7. Set up systemd services
```bash
mkdir -p ~/.fusion/logs
sudo cp deploy/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now fusion-dashboard.service
sudo systemctl enable --now cloudflared-tunnel.service
sudo systemctl status fusion-dashboard.service
```

## Running
```bash
# Manual start (for testing)
bash scripts/start-factory.sh start

# Check status
bash scripts/start-factory.sh status

# Stop
bash scripts/start-factory.sh stop
```

## Data Persistence
- **Global settings + DB**: `~/.fusion/` (includes `settings.json`, `embedded-postgres/`) - MUST be backed up
- **Project state**: `<repo>/.fusion/` (project.json, config.json, tasks/, agents/) - MUST be backed up
- **Agent state/memory**: `~/.fusion/agent/`, `<repo>/.fusion/agent-memory/`
- **Backups**: Use `scripts/fusion-factory-maintenance.sh backup`

## Security Notes
- Never commit secrets to Git
- Run services as a dedicated user (not root)
- Use bearer token authentication (do not use --no-auth in production)
- Keep cloudflared token secure
- Restrict firewall to necessary ports
- `fn dashboard` requires authentication by default (no --no-auth)
- Fusion v0.77.0 does not auto-load .env files - use `~/.fusion/settings.json`
