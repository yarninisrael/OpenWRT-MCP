# OpenWRT SSH MCP Server - Claude Desktop Installation Guide

Complete guide for installing and configuring the OpenWRT SSH MCP Server with Claude Desktop.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Installation Methods](#installation-methods)
   - [Method 1: Docker (Recommended)](#method-1-docker-recommended)
   - [Method 2: Direct Python](#method-2-direct-python)
4. [Router Setup](#router-setup)
5. [Claude Desktop Configuration](#claude-desktop-configuration)
6. [Testing Your Setup](#testing-your-setup)
7. [Available Tools](#available-tools)
8. [Example Usage](#example-usage)
9. [Troubleshooting](#troubleshooting)
10. [Security Considerations](#security-considerations)

---

## Overview

The OpenWRT SSH MCP Server enables Claude Desktop to manage your OpenWRT router through natural language commands. Once installed, you can ask Claude to:

- Check router system status and resource usage
- Manage WiFi networks and view connected devices
- Install or remove software packages
- Configure Thread/Matter networks
- View and manage firewall rules
- Read and search router configuration files

**Architecture:**
```
Claude Desktop (MCP Client)
        ↓
    MCP Protocol (stdio)
        ↓
Docker Container or Python Process
        ↓
    SSH Connection
        ↓
OpenWRT Router (192.168.1.1)
```

---

## Prerequisites

### System Requirements

| Component | Requirement |
|-----------|-------------|
| Operating System | Windows 10/11, macOS 10.15+, or Linux |
| Claude Desktop | Latest version installed |
| Docker (Method 1) | Docker Desktop 4.0+ |
| Python (Method 2) | Python 3.10 or higher |
| Network | Access to your OpenWRT router |

### Router Requirements

- OpenWRT-based router (any recent version)
- SSH access enabled on the router
- Root user credentials or SSH key configured
- Router accessible from your computer (typically 192.168.1.1)

---

## Installation Methods

### Method 1: Docker (Recommended)

Docker provides the most secure and isolated installation. This is the recommended method for production use.

#### Step 1: Install Docker Desktop

**Windows:**
1. Download Docker Desktop from https://www.docker.com/products/docker-desktop
2. Run the installer and follow the prompts
3. Restart your computer when prompted
4. Launch Docker Desktop and wait for it to start

**macOS:**
```bash
# Using Homebrew
brew install --cask docker

# Or download from https://www.docker.com/products/docker-desktop
```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install docker.io docker-compose
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
# Log out and back in for group changes to take effect
```

#### Step 2: Clone the Repository

```bash
# Clone the repository
git clone https://github.com/your-username/openwrt_ssh_mcp.git
cd openwrt_ssh_mcp

# Or download and extract the ZIP file
```

#### Step 3: Configure Environment Variables

```bash
# Copy the example configuration
cp .env.example .env
```

Edit the `.env` file with your router details:

```bash
# Router Connection Settings
OPENWRT_HOST=192.168.1.1          # Your router's IP address
OPENWRT_PORT=22                    # SSH port (usually 22)
OPENWRT_USER=root                  # SSH username

# Authentication - Choose ONE method:

# Option A: SSH Key (Recommended - more secure)
OPENWRT_KEY_FILE=/root/.ssh/openwrt_router

# Option B: Password (less secure, not recommended)
# OPENWRT_PASSWORD=your_router_password

# SSH Settings
SSH_TIMEOUT=30
SSH_KEEPALIVE_INTERVAL=15

# Security Settings (keep these enabled)
ENABLE_COMMAND_VALIDATION=true
ENABLE_AUDIT_LOGGING=true
LOG_FILE=/app/logs/openwrt_mcp.log
```

#### Step 4: Set Up SSH Key Authentication (Recommended)

Generate and configure SSH keys for secure, passwordless authentication:

**On your computer:**

```bash
# Generate a new SSH key pair
ssh-keygen -t ed25519 -f ~/.ssh/openwrt_router -C "OpenWRT MCP Server"

# When prompted for a passphrase, press Enter for no passphrase
# (required for automated connections)
```

**Copy the key to your router:**

```bash
# Copy your public key to the router
ssh-copy-id -i ~/.ssh/openwrt_router.pub root@192.168.1.1

# Enter your router's root password when prompted
```

**Verify the connection:**

```bash
# Test SSH connection with key
ssh -i ~/.ssh/openwrt_router root@192.168.1.1 "uname -a"

# You should see OpenWRT system information without entering a password
```

#### Step 5: Build the Docker Image

```bash
# Build the Docker image
docker build -t openwrt-ssh-mcp:latest .

# This will take a few minutes and create a ~271MB image
```

#### Step 6: Test the Docker Container

```bash
# Run a quick test (press Ctrl+C to exit)
docker run -i --rm \
  --network host \
  --env-file .env \
  --mount type=bind,src=$HOME/.ssh,dst=/root/.ssh,readonly \
  openwrt-ssh-mcp:latest
```

If successful, you'll see the MCP server start without errors.

---

### Method 2: Direct Python

For development or if you prefer not to use Docker.

#### Step 1: Install Python

**Windows:**
1. Download Python 3.10+ from https://www.python.org/downloads/
2. Run installer and CHECK "Add Python to PATH"
3. Complete installation

**macOS:**
```bash
# Using Homebrew
brew install python@3.11
```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip
```

#### Step 2: Clone and Set Up the Project

```bash
# Clone the repository
git clone https://github.com/your-username/openwrt_ssh_mcp.git
cd openwrt_ssh_mcp

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
# Linux/macOS:
source venv/bin/activate
# Windows:
.\venv\Scripts\activate

# Install the package
pip install -e .
```

#### Step 3: Configure Environment

```bash
# Copy and edit configuration
cp .env.example .env

# Edit .env with your settings (see Method 1, Step 3)
```

#### Step 4: Set Up SSH Keys

Follow the SSH key setup instructions from Method 1, Step 4.

#### Step 5: Test the Installation

```bash
# Activate virtual environment if not active
source venv/bin/activate  # Linux/macOS
# or
.\venv\Scripts\activate   # Windows

# Run the server (press Ctrl+C to exit)
python -m openwrt_ssh_mcp.server
```

---

## Router Setup

### Enable SSH on OpenWRT

If SSH is not already enabled on your router:

1. **Via LuCI Web Interface:**
   - Navigate to `http://192.168.1.1` in your browser
   - Go to **System** > **Administration**
   - Under **SSH Access**, ensure **Dropbear** is enabled on port 22
   - Click **Save & Apply**

2. **Set Root Password (if not set):**
   - Go to **System** > **Administration**
   - Enter and confirm a root password
   - Click **Save & Apply**

### Verify Router Access

```bash
# Test basic SSH connection
ssh root@192.168.1.1

# You should see the OpenWRT banner and shell prompt
```

---

## Claude Desktop Configuration

### Locate Configuration File

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```
Usually: `C:\Users\YourUsername\AppData\Roaming\Claude\claude_desktop_config.json`

**macOS:**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Linux:**
```
~/.config/Claude/claude_desktop_config.json
```

### Configuration for Docker (Recommended)

Create or edit `claude_desktop_config.json`:

**Windows:**
```json
{
  "mcpServers": {
    "openwrt-router": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "--network", "host",
        "--env-file", "C:\\Users\\YourUsername\\Projects\\openwrt_ssh_mcp\\.env",
        "--mount", "type=bind,src=C:\\Users\\YourUsername\\.ssh,dst=/root/.ssh,readonly",
        "--read-only",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges:true",
        "openwrt-ssh-mcp:latest"
      ]
    }
  }
}
```

**macOS/Linux:**
```json
{
  "mcpServers": {
    "openwrt-router": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "--network", "host",
        "--env-file", "/Users/yourusername/Projects/openwrt_ssh_mcp/.env",
        "--mount", "type=bind,src=/Users/yourusername/.ssh,dst=/root/.ssh,readonly",
        "--read-only",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges:true",
        "openwrt-ssh-mcp:latest"
      ]
    }
  }
}
```

### Configuration for Direct Python

**Windows:**
```json
{
  "mcpServers": {
    "openwrt-router": {
      "command": "C:\\Users\\YourUsername\\Projects\\openwrt_ssh_mcp\\venv\\Scripts\\python.exe",
      "args": ["-m", "openwrt_ssh_mcp.server"],
      "env": {
        "OPENWRT_HOST": "192.168.1.1",
        "OPENWRT_PORT": "22",
        "OPENWRT_USER": "root",
        "OPENWRT_KEY_FILE": "C:\\Users\\YourUsername\\.ssh\\openwrt_router",
        "ENABLE_COMMAND_VALIDATION": "true",
        "ENABLE_AUDIT_LOGGING": "true"
      }
    }
  }
}
```

**macOS/Linux:**
```json
{
  "mcpServers": {
    "openwrt-router": {
      "command": "/Users/yourusername/Projects/openwrt_ssh_mcp/venv/bin/python",
      "args": ["-m", "openwrt_ssh_mcp.server"],
      "env": {
        "OPENWRT_HOST": "192.168.1.1",
        "OPENWRT_PORT": "22",
        "OPENWRT_USER": "root",
        "OPENWRT_KEY_FILE": "/Users/yourusername/.ssh/openwrt_router",
        "ENABLE_COMMAND_VALIDATION": "true",
        "ENABLE_AUDIT_LOGGING": "true"
      }
    }
  }
}
```

### Apply Configuration

1. Save the `claude_desktop_config.json` file
2. **Completely quit Claude Desktop** (not just close the window)
   - Windows: Right-click system tray icon > Exit
   - macOS: Claude > Quit Claude (or Cmd+Q)
3. Relaunch Claude Desktop
4. The MCP server will now be available

---

## Testing Your Setup

### Verify MCP Server Connection

After restarting Claude Desktop, start a new conversation and ask:

```
Can you test the connection to my OpenWRT router?
```

Claude should use the `openwrt_test_connection` tool and report success.

### Basic Commands to Try

```
What's the system status of my router?
```

```
Show me the WiFi status and connected devices.
```

```
List the installed packages on my router.
```

---

## Available Tools

The MCP server provides 19 tools organized into categories:

### System & Network (8 tools)

| Tool | Description |
|------|-------------|
| `openwrt_test_connection` | Test SSH connection to router |
| `openwrt_execute_command` | Execute validated shell commands |
| `openwrt_get_system_info` | Get system details (uptime, memory, CPU) |
| `openwrt_restart_interface` | Restart network interfaces |
| `openwrt_get_wifi_status` | Get WiFi status and connected clients |
| `openwrt_list_dhcp_leases` | List DHCP clients with IP/MAC |
| `openwrt_get_firewall_rules` | View iptables firewall rules |
| `openwrt_read_config` | Read UCI configuration files |

### WiFi Management (4 tools)

| Tool | Description |
|------|-------------|
| `openwrt_wifi_control` | Control WiFi (up/down/reload/restart) |
| `openwrt_wifi_get_interfaces` | Get wireless interface details |
| `openwrt_wifi_scan` | Scan for nearby WiFi networks |
| `openwrt_wifi_get_clients` | Get connected WiFi clients |

### Package Management (6 tools)

| Tool | Description |
|------|-------------|
| `openwrt_opkg_update` | Update package lists |
| `openwrt_opkg_install` | Install packages |
| `openwrt_opkg_remove` | Remove packages |
| `openwrt_opkg_list_installed` | List installed packages |
| `openwrt_opkg_info` | Get package details |
| `openwrt_opkg_list_available` | List available packages |

### OpenThread/Matter (5 tools)

| Tool | Description |
|------|-------------|
| `openwrt_thread_get_state` | Get Thread network state |
| `openwrt_thread_create_network` | Create new Thread network |
| `openwrt_thread_get_dataset` | Get Thread network credentials |
| `openwrt_thread_get_info` | Get Thread network info |
| `openwrt_thread_enable_commissioner` | Enable device joining |

### File Operations (6 tools)

| Tool | Description |
|------|-------------|
| `openwrt_file_list` | List directory contents |
| `openwrt_file_read` | Read file contents |
| `openwrt_file_search` | Search files by name or content |
| `openwrt_file_stat` | Get file metadata |
| `openwrt_file_disk_usage` | Get disk usage info |
| `openwrt_file_mkdir` | Create directories |

---

## Example Usage

Once configured, you can ask Claude natural language questions:

### System Management

```
"What's my router's uptime and memory usage?"
"Show me the CPU load on the router"
"What version of OpenWRT is installed?"
```

### Network & WiFi

```
"Show me all devices connected to my WiFi"
"Scan for nearby WiFi networks"
"Restart the WAN interface"
"What are my current firewall rules?"
```

### Package Management

```
"List all installed packages"
"Install the luci-app-statistics package"
"Is the curl package installed?"
"Update the package list"
```

### Configuration

```
"Show me the wireless configuration"
"Read the DHCP configuration"
"What DNS servers are configured?"
```

### Thread/Matter (if OTBR is installed)

```
"What's the current Thread network state?"
"Create a new Thread network called 'HomeThread' on channel 15"
"Get the Thread network credentials"
```

### File Operations

```
"List files in /etc/config"
"Read the contents of /etc/banner"
"Search for files containing 'wireless'"
"How much disk space is available?"
```

---

## Troubleshooting

### Connection Issues

**Error: "Connection refused" or "Connection timed out"**

1. Verify router IP address:
   ```bash
   ping 192.168.1.1
   ```

2. Check SSH is enabled on router:
   ```bash
   ssh root@192.168.1.1
   ```

3. Verify firewall isn't blocking SSH:
   - Ensure port 22 is open on your computer's firewall

**Error: "Authentication failed"**

1. For SSH key auth:
   ```bash
   # Check key permissions
   chmod 600 ~/.ssh/openwrt_router
   chmod 644 ~/.ssh/openwrt_router.pub

   # Test key manually
   ssh -i ~/.ssh/openwrt_router -v root@192.168.1.1
   ```

2. For password auth:
   - Verify password is correct in `.env`
   - Try connecting manually: `ssh root@192.168.1.1`

### Docker Issues

**Error: "Docker not running"**

- Ensure Docker Desktop is running
- Windows: Check system tray for Docker icon
- macOS: Check menu bar for Docker icon

**Error: "Image not found"**

```bash
# Rebuild the image
docker build -t openwrt-ssh-mcp:latest .
```

**Error: "Cannot connect to Docker daemon"**

```bash
# Linux: Ensure you're in the docker group
sudo usermod -aG docker $USER
# Then log out and back in
```

### Claude Desktop Issues

**MCP Server not appearing**

1. Verify `claude_desktop_config.json` syntax:
   ```bash
   # Test JSON validity
   python -c "import json; json.load(open('claude_desktop_config.json'))"
   ```

2. Check file is in correct location (see Configuration section)

3. Completely quit and restart Claude Desktop

**Error: "Tool execution failed"**

1. Test the server manually:
   ```bash
   # Docker method
   docker run -i --rm --network host --env-file .env openwrt-ssh-mcp:latest

   # Python method
   python -m openwrt_ssh_mcp.server
   ```

2. Check the logs:
   ```bash
   cat openwrt_mcp.log
   ```

### Common Fixes

**Permission denied on SSH key (Linux/macOS):**
```bash
chmod 600 ~/.ssh/openwrt_router
chmod 700 ~/.ssh
```

**Windows path issues:**
- Use double backslashes in JSON: `C:\\Users\\...`
- Or use forward slashes: `C:/Users/...`

**Environment variable not loaded:**
- Ensure `.env` file exists in the project directory
- Check for typos in variable names
- Verify no extra spaces around `=` signs

---

## Security Considerations

### Best Practices

1. **Use SSH key authentication** instead of passwords
2. **Keep command validation enabled** (`ENABLE_COMMAND_VALIDATION=true`)
3. **Enable audit logging** (`ENABLE_AUDIT_LOGGING=true`)
4. **Use Docker** for additional isolation
5. **Don't store passwords in plain text** - use SSH keys instead

### What's Protected

The MCP server includes built-in security:

- **Command whitelist**: Only approved commands can be executed
- **Blocked dangerous commands**: `rm -rf`, `mkfs`, `dd`, `shutdown`, `reboot`, `passwd`
- **Audit logging**: All commands are logged with timestamps
- **Docker isolation**: Container runs with minimal privileges

### Docker Security Options

The recommended Docker configuration includes:

```bash
--read-only                           # Read-only filesystem
--cap-drop ALL                        # Drop all capabilities
--security-opt no-new-privileges:true # Prevent privilege escalation
--tmpfs /tmp:rw,noexec,nosuid        # Restricted temp directory
```

---

## Getting Help

- **GitHub Issues**: Report bugs or request features
- **Documentation**: See the `Documentation/` folder for additional guides
- **Logs**: Check `openwrt_mcp.log` for detailed error information

---

## Quick Reference

### Essential Commands

```bash
# Build Docker image
docker build -t openwrt-ssh-mcp:latest .

# Test Docker container
docker run -i --rm --network host --env-file .env openwrt-ssh-mcp:latest

# Test SSH connection
ssh -i ~/.ssh/openwrt_router root@192.168.1.1

# Check logs
cat openwrt_mcp.log
```

### Configuration File Locations

| OS | Claude Desktop Config |
|----|----------------------|
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

### Environment Variables Summary

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENWRT_HOST` | Yes | 192.168.1.1 | Router IP address |
| `OPENWRT_PORT` | No | 22 | SSH port |
| `OPENWRT_USER` | Yes | root | SSH username |
| `OPENWRT_KEY_FILE` | Recommended | - | Path to SSH private key |
| `OPENWRT_PASSWORD` | Alternative | - | SSH password (not recommended) |
| `ENABLE_COMMAND_VALIDATION` | No | true | Security whitelist |
| `ENABLE_AUDIT_LOGGING` | No | true | Command logging |

---

*Version 1.0.0 - OpenWRT SSH MCP Server*
