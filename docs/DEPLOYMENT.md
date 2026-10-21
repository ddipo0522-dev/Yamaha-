# Fusion Factory Deployment Guide (Ubuntu Server)

This guide is for deploying the Fusion factory (Runfusion v0.77.0) on a fresh Ubuntu server. 
This repository (`ddipo0522-dev/Yamaha-`) contains the workspace/project files; the Fusion CLI is installed globally via npm.

## Prerequisites

- Ubuntu 22.04/24.04 LTS
- Node.js 24.x (matching the version used in this Codespace)
- npm/pnpm
- PostgreSQL 15+ (for production; embedded PostgreSQL is used locally but production should use external DB)
- systemd

## Installation

### 1. Install Node.js
```bash
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### 2. Install Fusion CLI
```bash
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
Copy the example env file and fill in real values:
```bash
cp deploy/examples/.env.example .env
# Edit .env with your values - NEVER commit it
chmod 600 .env
```

### 6. Set up Fusion
```bash
# Initialize project
fn init --name Yamaha-

# Configure provider via settings or environment
# The OpenRouter API key must be set in ~/.fusion/settings.json or via environment
```

### 7. Set up systemd services
```bash
sudo cp deploy/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now fusion-dashboard.service
sudo systemctl enable --now cloudflared-tunnel.service
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
- Fusion settings: `~/.fusion/settings.json` (contains API keys - never commit)
- PostgreSQL data: `~/.fusion/embedded-postgres/` or external PostgreSQL
- Project state: `<repo>/.fusion/`
- Tasks: `<repo>/.fusion/tasks/`
- Backups: Use `scripts/fusion-factory-maintenance.sh backup`

## Security Notes
- Never commit secrets to Git
- Run services as a dedicated user (not root)
- Use bearer token authentication (do not use --no-auth in production)
- Keep cloudflared token secure
- Restrict firewall to necessary ports
