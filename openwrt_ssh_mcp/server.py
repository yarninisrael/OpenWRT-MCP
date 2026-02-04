"""MCP Server implementation for OpenWRT management via SSH."""

import asyncio
import logging
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .config import settings
from .ssh_client import ssh_client
from .tools import OpenWRTTools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
    ]
)

logger = logging.getLogger(__name__)

# Initialize MCP server
app = Server("openwrt-ssh-mcp")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available OpenWRT management tools."""
    return [
        Tool(
            name="openwrt_test_connection",
            description="Test SSH connection to the OpenWRT router",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="openwrt_execute_command",
            description=(
                "Execute a validated shell command on the OpenWRT router. "
                "Commands are validated against a security whitelist. "
                "Use this for commands not covered by other specialized tools."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute (must be in whitelist)",
                    },
                },
                "required": ["command"],
            },
        ),
        Tool(
            name="openwrt_get_system_info",
            description=(
                "Get comprehensive system information including board details, "
                "uptime, memory usage, and CPU load"
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="openwrt_restart_interface",
            description="Restart a network interface (e.g., wan, lan, wlan0)",
            inputSchema={
                "type": "object",
                "properties": {
                    "interface": {
                        "type": "string",
                        "description": "Interface name to restart (e.g., 'wan', 'lan')",
                    },
                },
                "required": ["interface"],
            },
        ),
        Tool(
            name="openwrt_get_wifi_status",
            description="Get WiFi status including connected clients and signal strength",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="openwrt_list_dhcp_leases",
            description="List all DHCP leases (connected devices with IP/MAC addresses)",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="openwrt_get_firewall_rules",
            description="Get current firewall rules (iptables)",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="openwrt_read_config",
            description=(
                "Read a UCI configuration file. "
                "Allowed configs: network, wireless, dhcp, firewall, system"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "config_name": {
                        "type": "string",
                        "description": "Configuration name (e.g., 'network', 'wireless')",
                        "enum": ["network", "wireless", "dhcp", "firewall", "system"],
                    },
                },
                "required": ["config_name"],
            },
        ),
        # File Operations Tools
        Tool(
            name="openwrt_file_list",
            description=(
                "List directory contents with details (permissions, owner, size, date). "
                "Similar to 'ls -la'. Use to explore the router filesystem."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path (default: /)",
                        "default": "/",
                    },
                    "options": {
                        "type": "string",
                        "description": "Optional ls flags: '-la', '-lh', '-R' for recursive",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="openwrt_file_read",
            description=(
                "Read file contents. Can read entire file or limit to first/last N lines. "
                "Use for viewing config files, logs, etc."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path (must be absolute, e.g., /etc/config/network)",
                    },
                    "lines": {
                        "type": "integer",
                        "description": "Optional - limit to N lines",
                    },
                    "from_end": {
                        "type": "boolean",
                        "description": "If true with lines, read last N lines (like tail)",
                        "default": False,
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="openwrt_file_search",
            description=(
                "Search for files by name or search within file contents. "
                "Uses 'find' for filename search, 'grep' for content search."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Search pattern (filename glob or grep regex)",
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory to search in (default: /etc)",
                        "default": "/etc",
                    },
                    "search_type": {
                        "type": "string",
                        "description": "'content' to search file contents (grep), 'filename' to search names (find)",
                        "enum": ["content", "filename"],
                        "default": "content",
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Search recursively (default: true)",
                        "default": True,
                    },
                },
                "required": ["pattern"],
            },
        ),
        Tool(
            name="openwrt_file_stat",
            description=(
                "Get detailed file information including permissions, owner, group, "
                "size, and timestamps (access, modify, change times)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File or directory path",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="openwrt_file_disk_usage",
            description="Get disk usage (size) for a directory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path (default: /)",
                        "default": "/",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="openwrt_file_mkdir",
            description=(
                "Create a directory on the router. Creates parent directories if needed. "
                "Protected system paths are blocked."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to create",
                    },
                },
                "required": ["path"],
            },
        ),
        # WiFi Management Tools
        Tool(
            name="openwrt_wifi_control",
            description=(
                "Control WiFi interfaces - restart all wireless, bring up, bring down, or reload configuration. "
                "Use this to apply wireless configuration changes or troubleshoot WiFi issues."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Action to perform: 'up', 'down', 'reload', or omit to restart all wireless",
                        "enum": ["up", "down", "reload"],
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="openwrt_wifi_get_interfaces",
            description=(
                "Get detailed information about all wireless interfaces including ESSID, channel, "
                "mode, signal strength, and encryption. Uses iwinfo for comprehensive data."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="openwrt_wifi_scan",
            description=(
                "Scan for nearby WiFi networks on a specific interface. "
                "Returns list of networks with ESSID, signal strength, channel, and encryption."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "interface": {
                        "type": "string",
                        "description": "Wireless interface name (e.g., 'wlan0', 'phy0-ap0', 'radio0')",
                    },
                },
                "required": ["interface"],
            },
        ),
        Tool(
            name="openwrt_wifi_get_clients",
            description=(
                "Get list of connected WiFi clients with MAC address, signal strength, "
                "and TX/RX rates. Can query specific interface or all interfaces."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "interface": {
                        "type": "string",
                        "description": "Optional - specific interface, or omit for all interfaces",
                    },
                },
                "required": [],
            },
        ),
        # OpenThread Border Router (OTBR) Tools
        Tool(
            name="openwrt_thread_get_state",
            description="Get current OpenThread network state (disabled, detached, child, router, leader)",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="openwrt_thread_create_network",
            description=(
                "Create a new Thread network with specified parameters. "
                "This will initialize a new Thread network, configure it, and start it. "
                "Returns network credentials including network key and dataset."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "network_name": {
                        "type": "string",
                        "description": "Network name (default: OpenWRT-Thread)",
                        "default": "OpenWRT-Thread",
                    },
                    "channel": {
                        "type": "integer",
                        "description": "Thread channel between 11-26 (default: 15)",
                        "minimum": 11,
                        "maximum": 26,
                        "default": 15,
                    },
                    "panid": {
                        "type": "string",
                        "description": "PAN ID in hex format (e.g., 0x1234). Auto-generated if not provided.",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="openwrt_thread_get_dataset",
            description=(
                "Get active Thread dataset (network credentials). "
                "Returns dataset in both human-readable and hex format for sharing."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="openwrt_thread_get_info",
            description=(
                "Get comprehensive Thread network information including state, "
                "channel, PAN ID, network name, IP addresses, neighbors, and children."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="openwrt_thread_enable_commissioner",
            description=(
                "Enable Thread Commissioner to allow new devices to join the network. "
                "Devices can join using the provided passphrase."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "passphrase": {
                        "type": "string",
                        "description": "Joiner passphrase for devices (default: THREAD123)",
                        "default": "THREAD123",
                    },
                },
                "required": [],
            },
        ),
        # Package Management (opkg) Tools
        Tool(
            name="openwrt_opkg_update",
            description="Update package lists from repositories (opkg update)",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="openwrt_opkg_install",
            description="Install a package using opkg",
            inputSchema={
                "type": "object",
                "properties": {
                    "package_name": {
                        "type": "string",
                        "description": "Name of the package to install (e.g., 'luci-app-openthread', 'ot-br-posix')",
                    },
                },
                "required": ["package_name"],
            },
        ),
        Tool(
            name="openwrt_opkg_remove",
            description="Remove a package using opkg",
            inputSchema={
                "type": "object",
                "properties": {
                    "package_name": {
                        "type": "string",
                        "description": "Name of the package to remove",
                    },
                },
                "required": ["package_name"],
            },
        ),
        Tool(
            name="openwrt_opkg_list_installed",
            description="List all installed packages on the router",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="openwrt_opkg_info",
            description="Get detailed information about a specific package",
            inputSchema={
                "type": "object",
                "properties": {
                    "package_name": {
                        "type": "string",
                        "description": "Name of the package",
                    },
                },
                "required": ["package_name"],
            },
        ),
        Tool(
            name="openwrt_opkg_list_available",
            description="List available packages from repositories (limited to 500 packages)",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool execution requests."""
    try:
        logger.info(f"Tool called: {name} with arguments: {arguments}")

        # Route to appropriate tool
        if name == "openwrt_test_connection":
            result = await OpenWRTTools.test_connection()

        elif name == "openwrt_execute_command":
            command = arguments.get("command")
            if not command:
                raise ValueError("Missing required argument: command")
            result = await OpenWRTTools.execute_command(command)

        elif name == "openwrt_get_system_info":
            result = await OpenWRTTools.get_system_info()

        elif name == "openwrt_restart_interface":
            interface = arguments.get("interface")
            if not interface:
                raise ValueError("Missing required argument: interface")
            result = await OpenWRTTools.restart_interface(interface)

        elif name == "openwrt_get_wifi_status":
            result = await OpenWRTTools.get_wifi_status()

        elif name == "openwrt_list_dhcp_leases":
            result = await OpenWRTTools.list_dhcp_leases()

        elif name == "openwrt_get_firewall_rules":
            result = await OpenWRTTools.get_firewall_rules()

        elif name == "openwrt_read_config":
            config_name = arguments.get("config_name")
            if not config_name:
                raise ValueError("Missing required argument: config_name")
            result = await OpenWRTTools.read_config(config_name)

        # File Operations tools
        elif name == "openwrt_file_list":
            path = arguments.get("path", "/")
            options = arguments.get("options")
            result = await OpenWRTTools.file_list(path, options)

        elif name == "openwrt_file_read":
            path = arguments.get("path")
            if not path:
                raise ValueError("Missing required argument: path")
            lines = arguments.get("lines")
            from_end = arguments.get("from_end", False)
            result = await OpenWRTTools.file_read(path, lines, from_end)

        elif name == "openwrt_file_search":
            pattern = arguments.get("pattern")
            if not pattern:
                raise ValueError("Missing required argument: pattern")
            path = arguments.get("path", "/etc")
            search_type = arguments.get("search_type", "content")
            recursive = arguments.get("recursive", True)
            result = await OpenWRTTools.file_search(pattern, path, search_type, recursive)

        elif name == "openwrt_file_stat":
            path = arguments.get("path")
            if not path:
                raise ValueError("Missing required argument: path")
            result = await OpenWRTTools.file_stat(path)

        elif name == "openwrt_file_disk_usage":
            path = arguments.get("path", "/")
            result = await OpenWRTTools.file_disk_usage(path)

        elif name == "openwrt_file_mkdir":
            path = arguments.get("path")
            if not path:
                raise ValueError("Missing required argument: path")
            result = await OpenWRTTools.file_mkdir(path)

        # WiFi Management tools
        elif name == "openwrt_wifi_control":
            action = arguments.get("action")
            result = await OpenWRTTools.wifi_control(action)

        elif name == "openwrt_wifi_get_interfaces":
            result = await OpenWRTTools.wifi_get_interfaces()

        elif name == "openwrt_wifi_scan":
            interface = arguments.get("interface")
            if not interface:
                raise ValueError("Missing required argument: interface")
            result = await OpenWRTTools.wifi_scan(interface)

        elif name == "openwrt_wifi_get_clients":
            interface = arguments.get("interface")
            result = await OpenWRTTools.wifi_get_clients(interface)

        # OpenThread Border Router tools
        elif name == "openwrt_thread_get_state":
            result = await OpenWRTTools.thread_get_state()

        elif name == "openwrt_thread_create_network":
            network_name = arguments.get("network_name", "OpenWRT-Thread")
            channel = arguments.get("channel", 15)
            panid = arguments.get("panid")
            result = await OpenWRTTools.thread_create_network(network_name, channel, panid)

        elif name == "openwrt_thread_get_dataset":
            result = await OpenWRTTools.thread_get_dataset()

        elif name == "openwrt_thread_get_info":
            result = await OpenWRTTools.thread_get_info()

        elif name == "openwrt_thread_enable_commissioner":
            passphrase = arguments.get("passphrase", "THREAD123")
            result = await OpenWRTTools.thread_enable_commissioner(passphrase)

        # Package management tools
        elif name == "openwrt_opkg_update":
            result = await OpenWRTTools.opkg_update()

        elif name == "openwrt_opkg_install":
            package_name = arguments.get("package_name")
            if not package_name:
                raise ValueError("Missing required argument: package_name")
            result = await OpenWRTTools.opkg_install(package_name)

        elif name == "openwrt_opkg_remove":
            package_name = arguments.get("package_name")
            if not package_name:
                raise ValueError("Missing required argument: package_name")
            result = await OpenWRTTools.opkg_remove(package_name)

        elif name == "openwrt_opkg_list_installed":
            result = await OpenWRTTools.opkg_list_installed()

        elif name == "openwrt_opkg_info":
            package_name = arguments.get("package_name")
            if not package_name:
                raise ValueError("Missing required argument: package_name")
            result = await OpenWRTTools.opkg_info(package_name)

        elif name == "openwrt_opkg_list_available":
            result = await OpenWRTTools.opkg_list_available()

        else:
            raise ValueError(f"Unknown tool: {name}")

        # Format response
        import json
        response_text = json.dumps(result, indent=2, ensure_ascii=False)

        return [
            TextContent(
                type="text",
                text=response_text,
            )
        ]

    except Exception as e:
        logger.error(f"Tool execution error: {e}", exc_info=True)
        error_response = {
            "success": False,
            "error": str(e),
        }
        import json
        return [
            TextContent(
                type="text",
                text=json.dumps(error_response, indent=2),
            )
        ]


async def main():
    """Main entry point for the MCP server."""
    try:
        # Validate configuration
        logger.info("Starting OpenWRT SSH MCP Server...")
        settings.validate_auth()
        
        logger.info(f"Target router: {settings.openwrt_host}:{settings.openwrt_port}")
        logger.info(f"SSH user: {settings.openwrt_user}")
        logger.info(f"Auth method: {'key-based' if settings.openwrt_key_file else 'password'}")
        logger.info(f"Command validation: {'enabled' if settings.enable_command_validation else 'DISABLED'}")
        logger.info(f"Audit logging: {'enabled' if settings.enable_audit_logging else 'disabled'}")

        # Connect to router
        logger.info("Establishing SSH connection...")
        connected = await ssh_client.connect()
        
        if not connected:
            logger.error("Failed to establish SSH connection. Server may not function properly.")
            logger.warning("Continuing anyway - connection will be retried on first tool call")

        # Run MCP server
        logger.info("MCP Server ready - waiting for requests...")
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options(),
            )

    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        raise
    finally:
        # Cleanup
        logger.info("Shutting down...")
        await ssh_client.disconnect()
        logger.info("Server stopped")


def run():
    """Run the server (used by setuptools entry point)."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
