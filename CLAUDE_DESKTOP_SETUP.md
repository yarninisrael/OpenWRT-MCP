# OpenWRT SSH MCP Server - Claude Desktop Installation Guide

Complete guide for installing and configuring the OpenWRT SSH MCP Server with Claude Desktop.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
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
    Python MCP Server
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
| Python | Python 3.10 or higher |
| Network | Access to your OpenWRT router |

### Router Requirements

- OpenWRT-based router (any recent version)
- SSH access enabled on the router
- Root user credentials or SSH key configured
- Router accessible from your computer (typically 192.168.1.1)

---

## Installation

### Step 1: Install Python

**Windows:**
1. Download Python 3.10+ from https://www.python.org/downloads/
2. Run installer and **CHECK "Add Python to PATH"**
3. Complete installation

**macOS:**
```bash
# Using Homebrew
brew install python@3.11

# Or download from https://www.python.org/downloads/
```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip
```

### Step 2: Clone the Repository

```bash
# Clone the repository
git clone https://github.com/yarninisrael/OpenWRT-MCP.git
cd OpenWRT-MCP
```

Or download and extract the ZIP file from GitHub.

### Step 3: Create Virtual Environment and Install

**Linux/macOS:**
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install the package
pip install -e .
```

**Windows:**
```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\activate

# Install the package
pip install -e .
```

### Step 4: Set Up SSH Key Authentication (Recommended)

Generate and configure SSH keys for secure, passwordless authentication:

**Generate SSH Key:**

```bash
# Generate a new SSH key pair
ssh-keygen -t ed25519 -f ~/.ssh/openwrt_router -C "OpenWRT MCP Server"

# When prompted for a passphrase, press Enter for no passphrase
# (required for automated connections)
```

**Windows users:** The key will be created at `C:\Users\YourUsername\.ssh\openwrt_router`

**Copy Key to Router:**

```bash
# Copy your public key to the router
ssh-copy-id -i ~/.ssh/openwrt_router.pub root@192.168.1.1

# Enter your router's root password when prompted
```

**Windows users without ssh-copy-id:**
```powershell
# Display your public key
type $env:USERPROFILE\.ssh\openwrt_router.pub

# Then SSH into router and add it manually
ssh root@192.168.1.1
# On router, paste key into /etc/dropbear/authorized_keys
```

**Verify Connection:**

```bash
# Test SSH connection with key
ssh -i ~/.ssh/openwrt_router root@192.168.1.1 "uname -a"

# You should see OpenWRT system information without entering a password
```

### Step 5: Test the Server

```bash
# Make sure virtual environment is activated
# Linux/macOS:
source venv/bin/activate
# Windows:
.\venv\Scripts\activate

# Set environment variables and run
export OPENWRT_HOST=192.168.1.1
export OPENWRT_USER=root
export OPENWRT_KEY_FILE=~/.ssh/openwrt_router
python -m openwrt_ssh_mcp.server
```

Press Ctrl+C to stop. If no errors appear, the server is working.

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

### Create/Edit Configuration

Create or edit the `claude_desktop_config.json` file:

**Windows Example:**
```json
{
  "mcpServers": {
    "openwrt-router": {
      "command": "C:\\Users\\YourUsername\\Projects\\OpenWRT-MCP\\venv\\Scripts\\python.exe",
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

**macOS Example:**
```json
{
  "mcpServers": {
    "openwrt-router": {
      "command": "/Users/yourusername/Projects/OpenWRT-MCP/venv/bin/python",
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

**Linux Example:**
```json
{
  "mcpServers": {
    "openwrt-router": {
      "command": "/home/yourusername/Projects/OpenWRT-MCP/venv/bin/python",
      "args": ["-m", "openwrt_ssh_mcp.server"],
      "env": {
        "OPENWRT_HOST": "192.168.1.1",
        "OPENWRT_PORT": "22",
        "OPENWRT_USER": "root",
        "OPENWRT_KEY_FILE": "/home/yourusername/.ssh/openwrt_router",
        "ENABLE_COMMAND_VALIDATION": "true",
        "ENABLE_AUDIT_LOGGING": "true"
      }
    }
  }
}
```

### Important Configuration Notes

1. **Replace paths** with your actual paths:
   - `YourUsername` → your actual username
   - Project path → where you cloned the repository

2. **Use the correct Python path**:
   - Must point to the Python inside your virtual environment
   - Windows: `...\venv\Scripts\python.exe`
   - macOS/Linux: `.../venv/bin/python`

3. **SSH key path** must match where you created your key

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

The MCP server provides 19+ tools organized into categories:

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

3. Verify firewall isn't blocking SSH

**Error: "Authentication failed"**

1. Check key permissions:
   ```bash
   # Linux/macOS
   chmod 600 ~/.ssh/openwrt_router
   chmod 644 ~/.ssh/openwrt_router.pub
   ```

2. Test key manually:
   ```bash
   ssh -i ~/.ssh/openwrt_router -v root@192.168.1.1
   ```

3. Ensure key was copied to router correctly

### Claude Desktop Issues

**MCP Server not appearing**

1. Verify `claude_desktop_config.json` syntax:
   ```bash
   # Test JSON validity
   python -c "import json; json.load(open('claude_desktop_config.json'))"
   ```

2. Check file is in correct location

3. Verify Python path is correct and points to venv

4. **Completely quit and restart Claude Desktop**

**Error: "Tool execution failed"**

1. Test the server manually:
   ```bash
   # Activate venv first
   source venv/bin/activate  # or .\venv\Scripts\activate on Windows

   # Set environment and run
   OPENWRT_HOST=192.168.1.1 OPENWRT_USER=root OPENWRT_KEY_FILE=~/.ssh/openwrt_router python -m openwrt_ssh_mcp.server
   ```

2. Look for error messages in the output

### Common Fixes

**"Module not found" error:**
```bash
# Make sure you're using the venv Python
which python  # Should show .../venv/bin/python

# If not, activate the venv
source venv/bin/activate

# Reinstall if needed
pip install -e .
```

**Permission denied on SSH key (Linux/macOS):**
```bash
chmod 600 ~/.ssh/openwrt_router
chmod 700 ~/.ssh
```

**Windows path issues:**
- Use double backslashes in JSON: `C:\\Users\\...`
- Or use forward slashes: `C:/Users/...`

**Python not found:**
- Ensure you're using the full path to the venv Python
- Windows: `C:\...\venv\Scripts\python.exe`
- macOS/Linux: `/.../venv/bin/python`

---

## Security Considerations

### Best Practices

1. **Use SSH key authentication** instead of passwords
2. **Keep command validation enabled** (`ENABLE_COMMAND_VALIDATION=true`)
3. **Enable audit logging** (`ENABLE_AUDIT_LOGGING=true`)
4. **Use a dedicated SSH key** just for MCP server access

### What's Protected

The MCP server includes built-in security:

- **Command whitelist**: Only approved commands can be executed
- **Blocked dangerous commands**: `rm -rf`, `mkfs`, `dd`, `shutdown`, `reboot`, `passwd`
- **Audit logging**: All commands are logged with timestamps

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENWRT_HOST` | Yes | 192.168.1.1 | Router IP address |
| `OPENWRT_PORT` | No | 22 | SSH port |
| `OPENWRT_USER` | Yes | root | SSH username |
| `OPENWRT_KEY_FILE` | Recommended | - | Path to SSH private key |
| `OPENWRT_PASSWORD` | Alternative | - | SSH password (not recommended) |
| `SSH_TIMEOUT` | No | 30 | Connection timeout in seconds |
| `ENABLE_COMMAND_VALIDATION` | No | true | Enable security whitelist |
| `ENABLE_AUDIT_LOGGING` | No | true | Enable command logging |
| `LOG_FILE` | No | - | Path to log file |

---

## Quick Reference

### Installation Summary

```bash
# 1. Clone repository
git clone https://github.com/yarninisrael/OpenWRT-MCP.git
cd OpenWRT-MCP

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# .\venv\Scripts\activate  # Windows

# 3. Install package
pip install -e .

# 4. Set up SSH key
ssh-keygen -t ed25519 -f ~/.ssh/openwrt_router
ssh-copy-id -i ~/.ssh/openwrt_router.pub root@192.168.1.1

# 5. Configure Claude Desktop (edit claude_desktop_config.json)
# 6. Restart Claude Desktop
```

### Configuration File Locations

| OS | Claude Desktop Config |
|----|----------------------|
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

---

## Getting Help

- **GitHub Issues**: https://github.com/yarninisrael/OpenWRT-MCP/issues
- **Documentation**: See other files in the repository for additional guides

---

*Version 1.0.0 - OpenWRT SSH MCP Server*
