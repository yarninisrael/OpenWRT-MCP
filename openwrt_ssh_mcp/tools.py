"""OpenWRT-specific tools for MCP server."""

import json
import logging
import re
from typing import Any

from .ssh_client import ssh_client
from .security import SecurityValidator

logger = logging.getLogger(__name__)


class OpenWRTTools:
    """Collection of OpenWRT management tools."""

    @staticmethod
    async def execute_command(command: str) -> dict[str, Any]:
        """
        Execute a validated command on the OpenWRT router.
        
        Args:
            command: Shell command to execute
            
        Returns:
            dict: Execution result
        """
        # Validate command
        is_valid, error_msg = SecurityValidator.validate_command(command)
        if not is_valid:
            return {
                "success": False,
                "error": error_msg,
                "output": "",
            }

        # Execute
        await ssh_client.ensure_connected()
        result = await ssh_client.execute(command)

        return {
            "success": result["success"],
            "output": result["stdout"],
            "error": result["stderr"],
            "exit_code": result["exit_code"],
            "execution_time": result["execution_time"],
        }

    @staticmethod
    async def get_system_info() -> dict[str, Any]:
        """
        Get OpenWRT system information (uptime, memory, load).
        
        Returns:
            dict: System information
        """
        try:
            await ssh_client.ensure_connected()

            # Execute multiple commands to gather system info
            commands = {
                "board": "ubus call system board",
                "info": "ubus call system info",
                "uptime": "cat /proc/uptime",
                "loadavg": "cat /proc/loadavg",
            }

            results = {}
            for key, cmd in commands.items():
                result = await ssh_client.execute(cmd)
                if result["success"]:
                    if key in ["board", "info"]:
                        # Parse JSON output from ubus
                        try:
                            results[key] = json.loads(result["stdout"])
                        except json.JSONDecodeError:
                            results[key] = result["stdout"]
                    else:
                        results[key] = result["stdout"]
                else:
                    results[key] = {"error": result["stderr"]}

            return {
                "success": True,
                "system_info": results,
            }

        except Exception as e:
            logger.error(f"Failed to get system info: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    @staticmethod
    async def restart_interface(interface: str) -> dict[str, Any]:
        """
        Restart a network interface.
        
        Args:
            interface: Interface name (e.g., 'wan', 'lan')
            
        Returns:
            dict: Operation result
        """
        command = f"ubus call network.interface.{interface} restart"
        
        # Validate interface name (alphanumeric and underscore only)
        if not interface.replace("_", "").isalnum():
            return {
                "success": False,
                "error": "Invalid interface name",
            }

        result = await OpenWRTTools.execute_command(command)
        
        if result["success"]:
            return {
                "success": True,
                "message": f"Interface '{interface}' restarted successfully",
                "output": result["output"],
            }
        else:
            return {
                "success": False,
                "error": f"Failed to restart interface '{interface}': {result['error']}",
            }

    @staticmethod
    async def get_wifi_status() -> dict[str, Any]:
        """
        Get WiFi status and connected clients.
        
        Returns:
            dict: WiFi status information
        """
        command = "ubus call network.wireless status"
        result = await OpenWRTTools.execute_command(command)

        if result["success"]:
            try:
                wifi_data = json.loads(result["output"])
                return {
                    "success": True,
                    "wifi_status": wifi_data,
                }
            except json.JSONDecodeError:
                return {
                    "success": True,
                    "wifi_status": result["output"],
                }
        else:
            return {
                "success": False,
                "error": result["error"],
            }

    @staticmethod
    async def list_dhcp_leases() -> dict[str, Any]:
        """
        List DHCP leases (connected devices).
        
        Returns:
            dict: DHCP leases information
        """
        # Try both possible locations for DHCP leases file
        commands = [
            "cat /tmp/dhcp.leases",
            "cat /var/dhcp.leases",
        ]

        for cmd in commands:
            result = await OpenWRTTools.execute_command(cmd)
            if result["success"] and result["output"]:
                # Parse DHCP leases
                leases = []
                for line in result["output"].strip().split("\n"):
                    if line:
                        parts = line.split()
                        if len(parts) >= 4:
                            leases.append({
                                "timestamp": parts[0],
                                "mac": parts[1],
                                "ip": parts[2],
                                "hostname": parts[3] if len(parts) > 3 else "",
                                "client_id": parts[4] if len(parts) > 4 else "",
                            })

                return {
                    "success": True,
                    "leases": leases,
                    "count": len(leases),
                }

        return {
            "success": False,
            "error": "Could not read DHCP leases file",
        }

    @staticmethod
    async def get_firewall_rules() -> dict[str, Any]:
        """
        Get firewall rules.
        
        Returns:
            dict: Firewall rules
        """
        command = "iptables -L -n -v"
        result = await OpenWRTTools.execute_command(command)

        if result["success"]:
            return {
                "success": True,
                "rules": result["output"],
            }
        else:
            return {
                "success": False,
                "error": result["error"],
            }

    @staticmethod
    async def read_config(config_name: str) -> dict[str, Any]:
        """
        Read a UCI configuration file.
        
        Args:
            config_name: Configuration name (e.g., 'network', 'wireless', 'dhcp')
            
        Returns:
            dict: Configuration content
        """
        # Whitelist of allowed config names
        allowed_configs = ["network", "wireless", "dhcp", "firewall", "system"]
        
        if config_name not in allowed_configs:
            return {
                "success": False,
                "error": f"Configuration '{config_name}' not allowed. Allowed: {', '.join(allowed_configs)}",
            }

        command = f"uci show {config_name}"
        result = await OpenWRTTools.execute_command(command)

        if result["success"]:
            return {
                "success": True,
                "config_name": config_name,
                "config": result["output"],
            }
        else:
            return {
                "success": False,
                "error": result["error"],
            }

    @staticmethod
    async def test_connection() -> dict[str, Any]:
        """
        Test SSH connection to the router.
        
        Returns:
            dict: Connection test result
        """
        return await ssh_client.test_connection()

    # ========== OpenThread Border Router (OTBR) Tools ==========

    @staticmethod
    async def thread_get_state() -> dict[str, Any]:
        """
        Get current OpenThread state.
        
        Returns:
            dict: Thread state (disabled, detached, child, router, leader)
        """
        command = "/usr/sbin/ot-ctl state"
        result = await OpenWRTTools.execute_command(command)

        if result["success"]:
            return {
                "success": True,
                "state": result["output"].strip(),
            }
        else:
            return {
                "success": False,
                "error": result["error"],
            }

    @staticmethod
    async def thread_create_network(
        network_name: str = "OpenWRT-Thread",
        channel: int = 15,
        panid: str = None,
    ) -> dict[str, Any]:
        """
        Create a new Thread network.
        
        Args:
            network_name: Network name (default: OpenWRT-Thread)
            channel: Thread channel 11-26 (default: 15)
            panid: PAN ID in hex format (auto-generated if not provided)
            
        Returns:
            dict: Operation result with network credentials
        """
        try:
            await ssh_client.ensure_connected()

            # Validate parameters
            if not network_name.replace("-", "").replace("_", "").isalnum():
                return {
                    "success": False,
                    "error": "Invalid network name. Use only alphanumeric, dash, and underscore.",
                }

            if not (11 <= channel <= 26):
                return {
                    "success": False,
                    "error": "Channel must be between 11 and 26",
                }

            # Generate random PAN ID if not provided
            if not panid:
                import secrets
                panid = f"0x{secrets.randbelow(0xFFFF):04x}"

            # Step 1: Initialize new dataset
            result = await ssh_client.execute("/usr/sbin/ot-ctl dataset init new")
            if not result["success"]:
                return {
                    "success": False,
                    "error": f"Failed to initialize dataset: {result['stderr']}",
                }

            # Step 2: Set network parameters
            commands = [
                f"/usr/sbin/ot-ctl channel {channel}",
                f"/usr/sbin/ot-ctl panid {panid}",
                f"/usr/sbin/ot-ctl networkname {network_name}",
            ]

            for cmd in commands:
                result = await ssh_client.execute(cmd)
                if not result["success"]:
                    return {
                        "success": False,
                        "error": f"Failed to execute '{cmd}': {result['stderr']}",
                    }

            # Step 3: Commit dataset
            result = await ssh_client.execute("/usr/sbin/ot-ctl dataset commit active")
            if not result["success"]:
                return {
                    "success": False,
                    "error": f"Failed to commit dataset: {result['stderr']}",
                }

            # Step 4: Bring up interface
            result = await ssh_client.execute("/usr/sbin/ot-ctl ifconfig up")
            if not result["success"]:
                return {
                    "success": False,
                    "error": f"Failed to bring up interface: {result['stderr']}",
                }

            # Step 5: Start Thread
            result = await ssh_client.execute("/usr/sbin/ot-ctl thread start")
            if not result["success"]:
                return {
                    "success": False,
                    "error": f"Failed to start Thread: {result['stderr']}",
                }

            # Step 6: Get network credentials
            import asyncio
            await asyncio.sleep(2)  # Wait for network to stabilize

            credentials = {}
            
            # Get network key
            result = await ssh_client.execute("/usr/sbin/ot-ctl networkkey")
            if result["success"]:
                credentials["network_key"] = result["stdout"].strip()

            # Get extended PAN ID
            result = await ssh_client.execute("/usr/sbin/ot-ctl extpanid")
            if result["success"]:
                credentials["ext_panid"] = result["stdout"].strip()

            # Get dataset in hex format
            result = await ssh_client.execute("/usr/sbin/ot-ctl dataset active -x")
            if result["success"]:
                credentials["dataset_hex"] = result["stdout"].strip()

            # Get current state
            result = await ssh_client.execute("/usr/sbin/ot-ctl state")
            if result["success"]:
                credentials["state"] = result["stdout"].strip()

            return {
                "success": True,
                "message": f"Thread network '{network_name}' created successfully",
                "network_name": network_name,
                "channel": channel,
                "panid": panid,
                "credentials": credentials,
            }

        except Exception as e:
            logger.error(f"Failed to create Thread network: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    @staticmethod
    async def thread_get_dataset() -> dict[str, Any]:
        """
        Get active Thread dataset (network credentials).
        
        Returns:
            dict: Active dataset information
        """
        command = "/usr/sbin/ot-ctl dataset active"
        result = await OpenWRTTools.execute_command(command)

        if result["success"]:
            # Also get hex format for easy sharing
            hex_result = await OpenWRTTools.execute_command("/usr/sbin/ot-ctl dataset active -x")
            
            return {
                "success": True,
                "dataset": result["output"],
                "dataset_hex": hex_result["output"].strip() if hex_result["success"] else None,
            }
        else:
            return {
                "success": False,
                "error": result["error"],
            }

    @staticmethod
    async def thread_get_info() -> dict[str, Any]:
        """
        Get comprehensive Thread network information.
        
        Returns:
            dict: Network state, neighbors, routes, etc.
        """
        try:
            await ssh_client.ensure_connected()

            info = {}

            # Get various Thread info
            commands = {
                "state": "/usr/sbin/ot-ctl state",
                "channel": "/usr/sbin/ot-ctl channel",
                "panid": "/usr/sbin/ot-ctl panid",
                "networkname": "/usr/sbin/ot-ctl networkname",
                "extpanid": "/usr/sbin/ot-ctl extpanid",
                "ipaddr": "/usr/sbin/ot-ctl ipaddr",
                "rloc16": "/usr/sbin/ot-ctl rloc16",
                "leaderdata": "/usr/sbin/ot-ctl leaderdata",
                "neighbor_table": "/usr/sbin/ot-ctl neighbor table",
                "child_table": "/usr/sbin/ot-ctl child table",
            }

            for key, cmd in commands.items():
                result = await ssh_client.execute(cmd)
                if result["success"]:
                    info[key] = result["stdout"].strip()
                else:
                    info[key] = None

            return {
                "success": True,
                "thread_info": info,
            }

        except Exception as e:
            logger.error(f"Failed to get Thread info: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    @staticmethod
    async def thread_enable_commissioner(passphrase: str = "THREAD123") -> dict[str, Any]:
        """
        Enable Thread Commissioner to allow devices to join.
        
        Args:
            passphrase: Joiner passphrase (default: THREAD123)
            
        Returns:
            dict: Operation result
        """
        try:
            await ssh_client.ensure_connected()

            # Start commissioner
            result = await ssh_client.execute("/usr/sbin/ot-ctl commissioner start")
            if not result["success"]:
                return {
                    "success": False,
                    "error": f"Failed to start commissioner: {result['stderr']}",
                }

            # Add joiner with wildcard (any device can join with this passphrase)
            result = await ssh_client.execute(f"/usr/sbin/ot-ctl commissioner joiner add * {passphrase}")
            if not result["success"]:
                return {
                    "success": False,
                    "error": f"Failed to add joiner: {result['stderr']}",
                }

            return {
                "success": True,
                "message": "Thread Commissioner enabled",
                "passphrase": passphrase,
                "note": "Devices can now join using this passphrase",
            }

        except Exception as e:
            logger.error(f"Failed to enable commissioner: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    # ========== File Operations Tools ==========

    @staticmethod
    async def file_list(path: str = "/", options: str = None) -> dict[str, Any]:
        """
        List directory contents.

        Args:
            path: Directory path (default: /)
            options: Optional ls flags like '-la', '-lh', '-R'

        Returns:
            dict: Directory listing
        """
        # Validate path - must be absolute
        if not path.startswith("/"):
            return {
                "success": False,
                "error": "Path must be absolute (start with /)",
            }

        # Sanitize path
        if ".." in path:
            return {
                "success": False,
                "error": "Path traversal not allowed",
            }

        # Build command
        if options and re.match(r'^-[lahtRrS1]+$', options):
            command = f"ls {options} {path}"
        else:
            command = f"ls -la {path}"

        result = await OpenWRTTools.execute_command(command)

        if result["success"]:
            # Parse ls output into structured data
            entries = []
            lines = result["output"].strip().split("\n")

            for line in lines:
                if not line or line.startswith("total"):
                    continue

                parts = line.split(None, 8)
                if len(parts) >= 9:
                    entries.append({
                        "permissions": parts[0],
                        "links": parts[1],
                        "owner": parts[2],
                        "group": parts[3],
                        "size": parts[4],
                        "date": f"{parts[5]} {parts[6]} {parts[7]}",
                        "name": parts[8],
                        "is_dir": parts[0].startswith("d"),
                        "is_link": parts[0].startswith("l"),
                    })
                elif len(parts) >= 1:
                    entries.append({"name": parts[-1]})

            return {
                "success": True,
                "path": path,
                "entries": entries,
                "count": len(entries),
                "raw_output": result["output"],
            }
        else:
            return {
                "success": False,
                "error": result["error"],
            }

    @staticmethod
    async def file_read(path: str, lines: int = None, from_end: bool = False) -> dict[str, Any]:
        """
        Read file contents.

        Args:
            path: File path (must be absolute)
            lines: Optional - limit to N lines
            from_end: If True with lines, read last N lines (tail), otherwise first N (head)

        Returns:
            dict: File contents
        """
        # Validate path
        if not path.startswith("/"):
            return {
                "success": False,
                "error": "Path must be absolute (start with /)",
            }

        if ".." in path:
            return {
                "success": False,
                "error": "Path traversal not allowed",
            }

        # Build command
        if lines and isinstance(lines, int) and lines > 0:
            if from_end:
                command = f"tail -n {lines} {path}"
            else:
                command = f"head -n {lines} {path}"
        else:
            command = f"cat {path}"

        result = await OpenWRTTools.execute_command(command)

        if result["success"]:
            return {
                "success": True,
                "path": path,
                "content": result["output"],
                "line_count": len(result["output"].split("\n")),
            }
        else:
            return {
                "success": False,
                "error": result["error"],
            }

    @staticmethod
    async def file_search(
        pattern: str,
        path: str = "/etc",
        search_type: str = "content",
        recursive: bool = True,
    ) -> dict[str, Any]:
        """
        Search for files or content.

        Args:
            pattern: Search pattern (filename pattern or grep pattern)
            path: Directory to search in (default: /etc)
            search_type: 'content' (grep) or 'filename' (find)
            recursive: Search recursively (default: True)

        Returns:
            dict: Search results
        """
        # Validate path
        if not path.startswith("/"):
            return {
                "success": False,
                "error": "Path must be absolute (start with /)",
            }

        if ".." in path:
            return {
                "success": False,
                "error": "Path traversal not allowed",
            }

        # Sanitize pattern - basic check
        if any(c in pattern for c in [";", "|", "&", "$", "`", "(", ")"]):
            return {
                "success": False,
                "error": "Invalid characters in pattern",
            }

        if search_type == "content":
            # Use grep
            flags = "-r" if recursive else ""
            command = f"grep {flags} '{pattern}' {path}"
        elif search_type == "filename":
            # Use find
            command = f"find {path} -name '{pattern}'"
        else:
            return {
                "success": False,
                "error": "search_type must be 'content' or 'filename'",
            }

        result = await OpenWRTTools.execute_command(command)

        if result["success"]:
            matches = [line for line in result["output"].strip().split("\n") if line]
            return {
                "success": True,
                "pattern": pattern,
                "path": path,
                "search_type": search_type,
                "matches": matches,
                "count": len(matches),
            }
        else:
            # grep returns exit code 1 if no matches - not an error
            if "exit_code" in result and result.get("exit_code") == 1:
                return {
                    "success": True,
                    "pattern": pattern,
                    "path": path,
                    "search_type": search_type,
                    "matches": [],
                    "count": 0,
                }
            return {
                "success": False,
                "error": result["error"],
            }

    @staticmethod
    async def file_stat(path: str) -> dict[str, Any]:
        """
        Get detailed file/directory information.

        Args:
            path: File or directory path

        Returns:
            dict: File statistics
        """
        # Validate path
        if not path.startswith("/"):
            return {
                "success": False,
                "error": "Path must be absolute (start with /)",
            }

        if ".." in path:
            return {
                "success": False,
                "error": "Path traversal not allowed",
            }

        command = f"stat {path}"
        result = await OpenWRTTools.execute_command(command)

        if result["success"]:
            # Parse stat output
            info = {"raw": result["output"]}
            for line in result["output"].split("\n"):
                if "Size:" in line:
                    size_match = re.search(r'Size:\s*(\d+)', line)
                    if size_match:
                        info["size_bytes"] = int(size_match.group(1))
                    type_match = re.search(r'Type:\s*(\w+)', line)
                    if type_match:
                        info["type"] = type_match.group(1)
                elif "Access:" in line and "Uid:" in line:
                    perm_match = re.search(r'Access:\s*\((\d+)/([^)]+)\)', line)
                    if perm_match:
                        info["permissions_octal"] = perm_match.group(1)
                        info["permissions"] = perm_match.group(2)
                    uid_match = re.search(r'Uid:\s*\(\s*(\d+)/\s*(\w+)\)', line)
                    if uid_match:
                        info["uid"] = int(uid_match.group(1))
                        info["owner"] = uid_match.group(2)
                    gid_match = re.search(r'Gid:\s*\(\s*(\d+)/\s*(\w+)\)', line)
                    if gid_match:
                        info["gid"] = int(gid_match.group(1))
                        info["group"] = gid_match.group(2)
                elif line.strip().startswith("Access:") and "Uid" not in line:
                    info["access_time"] = line.split(":", 1)[1].strip()
                elif line.strip().startswith("Modify:"):
                    info["modify_time"] = line.split(":", 1)[1].strip()
                elif line.strip().startswith("Change:"):
                    info["change_time"] = line.split(":", 1)[1].strip()

            return {
                "success": True,
                "path": path,
                "info": info,
            }
        else:
            return {
                "success": False,
                "error": result["error"],
            }

    @staticmethod
    async def file_disk_usage(path: str = "/") -> dict[str, Any]:
        """
        Get disk usage for a path.

        Args:
            path: Directory path (default: /)

        Returns:
            dict: Disk usage information
        """
        # Validate path
        if not path.startswith("/"):
            return {
                "success": False,
                "error": "Path must be absolute (start with /)",
            }

        if ".." in path:
            return {
                "success": False,
                "error": "Path traversal not allowed",
            }

        command = f"du -sh {path}"
        result = await OpenWRTTools.execute_command(command)

        if result["success"]:
            parts = result["output"].strip().split()
            return {
                "success": True,
                "path": path,
                "size": parts[0] if parts else "unknown",
                "raw_output": result["output"],
            }
        else:
            return {
                "success": False,
                "error": result["error"],
            }

    @staticmethod
    async def file_mkdir(path: str) -> dict[str, Any]:
        """
        Create a directory.

        Args:
            path: Directory path to create

        Returns:
            dict: Operation result
        """
        # Validate path
        if not path.startswith("/"):
            return {
                "success": False,
                "error": "Path must be absolute (start with /)",
            }

        if ".." in path:
            return {
                "success": False,
                "error": "Path traversal not allowed",
            }

        # Block sensitive paths
        blocked_paths = ["/etc", "/bin", "/sbin", "/usr", "/lib", "/root", "/sys", "/proc", "/dev"]
        for blocked in blocked_paths:
            if path == blocked or path.rstrip("/") == blocked:
                return {
                    "success": False,
                    "error": f"Cannot create directory at protected path: {blocked}",
                }

        command = f"mkdir -p {path}"
        result = await OpenWRTTools.execute_command(command)

        if result["success"]:
            return {
                "success": True,
                "message": f"Directory created: {path}",
            }
        else:
            return {
                "success": False,
                "error": result["error"],
            }

    # ========== WiFi Management Tools ==========

    @staticmethod
    async def wifi_control(action: str = None) -> dict[str, Any]:
        """
        Control WiFi interfaces (restart, up, down, reload).

        Args:
            action: Optional action - 'up', 'down', 'reload', or None to restart

        Returns:
            dict: Operation result
        """
        if action and action not in ["up", "down", "reload"]:
            return {
                "success": False,
                "error": f"Invalid action '{action}'. Use 'up', 'down', 'reload', or omit for restart.",
            }

        command = f"wifi {action}" if action else "wifi"
        result = await OpenWRTTools.execute_command(command)

        if result["success"]:
            return {
                "success": True,
                "message": f"WiFi {'restarted' if not action else action} successfully",
                "output": result["output"],
            }
        else:
            return {
                "success": False,
                "error": result["error"],
                "output": result["output"],
            }

    @staticmethod
    async def wifi_get_interfaces() -> dict[str, Any]:
        """
        Get detailed information about all wireless interfaces using iwinfo.

        Returns:
            dict: Wireless interface information
        """
        command = "iwinfo"
        result = await OpenWRTTools.execute_command(command)

        if result["success"]:
            # Parse iwinfo output into structured data
            interfaces = []
            current_iface = None

            for line in result["output"].split("\n"):
                if line and not line.startswith(" ") and not line.startswith("\t"):
                    # New interface line
                    if current_iface:
                        interfaces.append(current_iface)
                    parts = line.split()
                    current_iface = {
                        "name": parts[0] if parts else "",
                        "essid": "",
                        "raw": line,
                        "details": {}
                    }
                    # Extract ESSID if present
                    if 'ESSID:' in line:
                        essid_match = re.search(r'ESSID:\s*"([^"]*)"', line)
                        if essid_match:
                            current_iface["essid"] = essid_match.group(1)
                elif current_iface and line.strip():
                    # Detail line - parse key-value pairs
                    line = line.strip()
                    if ":" in line:
                        key, _, value = line.partition(":")
                        current_iface["details"][key.strip().lower().replace(" ", "_")] = value.strip()

            if current_iface:
                interfaces.append(current_iface)

            return {
                "success": True,
                "interfaces": interfaces,
                "count": len(interfaces),
                "raw_output": result["output"],
            }
        else:
            return {
                "success": False,
                "error": result["error"],
            }

    @staticmethod
    async def wifi_scan(interface: str) -> dict[str, Any]:
        """
        Scan for nearby WiFi networks.

        Args:
            interface: Wireless interface name (e.g., 'wlan0', 'phy0-ap0')

        Returns:
            dict: List of detected networks
        """
        # Validate interface name
        if not re.match(r'^[\w-]+$', interface):
            return {
                "success": False,
                "error": "Invalid interface name",
            }

        command = f"iwinfo {interface} scan"
        result = await OpenWRTTools.execute_command(command)

        if result["success"]:
            # Parse scan results
            networks = []
            current_network = None

            for line in result["output"].split("\n"):
                line = line.strip()
                if not line:
                    continue

                # New network entry starts with Cell or ESSID
                if line.startswith("Cell") or (line.startswith("ESSID:") and current_network is None):
                    if current_network:
                        networks.append(current_network)
                    current_network = {"raw_lines": [line]}
                elif current_network:
                    current_network["raw_lines"].append(line)

                    # Extract common fields
                    if "ESSID:" in line:
                        match = re.search(r'ESSID:\s*"([^"]*)"', line)
                        if match:
                            current_network["essid"] = match.group(1)
                    elif "Signal:" in line:
                        match = re.search(r'Signal:\s*(-?\d+)', line)
                        if match:
                            current_network["signal_dbm"] = int(match.group(1))
                    elif "Channel:" in line:
                        match = re.search(r'Channel:\s*(\d+)', line)
                        if match:
                            current_network["channel"] = int(match.group(1))
                    elif "Encryption:" in line:
                        current_network["encryption"] = line.split(":", 1)[1].strip()

            if current_network:
                networks.append(current_network)

            return {
                "success": True,
                "interface": interface,
                "networks": networks,
                "count": len(networks),
            }
        else:
            return {
                "success": False,
                "error": result["error"],
            }

    @staticmethod
    async def wifi_get_clients(interface: str = None) -> dict[str, Any]:
        """
        Get connected WiFi clients with signal strength and stats.

        Args:
            interface: Optional - specific interface, or None for all interfaces

        Returns:
            dict: Connected clients information
        """
        await ssh_client.ensure_connected()

        clients = []

        if interface:
            # Validate interface name
            if not re.match(r'^[\w-]+$', interface):
                return {
                    "success": False,
                    "error": "Invalid interface name",
                }
            interfaces = [interface]
        else:
            # Get all wireless interfaces first
            result = await ssh_client.execute("iwinfo")
            if not result["success"]:
                return {
                    "success": False,
                    "error": f"Failed to list interfaces: {result['stderr']}",
                }
            # Extract interface names
            interfaces = re.findall(r'^(\w+)\s+ESSID:', result["stdout"], re.MULTILINE)

        # Get associated clients for each interface
        for iface in interfaces:
            result = await ssh_client.execute(f"iwinfo {iface} assoclist")
            if result["success"] and result["stdout"].strip():
                # Parse assoclist output
                for line in result["stdout"].split("\n"):
                    if line.strip():
                        client = {"interface": iface, "raw": line}
                        # Extract MAC address
                        mac_match = re.search(r'([0-9A-Fa-f:]{17})', line)
                        if mac_match:
                            client["mac"] = mac_match.group(1)
                        # Extract signal
                        signal_match = re.search(r'(-?\d+)\s*dBm', line)
                        if signal_match:
                            client["signal_dbm"] = int(signal_match.group(1))
                        # Extract TX/RX rates
                        tx_match = re.search(r'TX:\s*([\d.]+)\s*MBit', line)
                        if tx_match:
                            client["tx_rate_mbps"] = float(tx_match.group(1))
                        rx_match = re.search(r'RX:\s*([\d.]+)\s*MBit', line)
                        if rx_match:
                            client["rx_rate_mbps"] = float(rx_match.group(1))

                        if "mac" in client:  # Only add if we found a MAC
                            clients.append(client)

        return {
            "success": True,
            "clients": clients,
            "count": len(clients),
        }

    # ========== Package Management (opkg) Tools ==========

    @staticmethod
    async def opkg_update() -> dict[str, Any]:
        """
        Update package lists from repositories.
        
        Returns:
            dict: Operation result
        """
        command = "opkg update"
        result = await OpenWRTTools.execute_command(command)

        if result["success"]:
            return {
                "success": True,
                "message": "Package lists updated successfully",
                "output": result["output"],
            }
        else:
            return {
                "success": False,
                "error": f"Failed to update package lists: {result['error']}",
            }

    @staticmethod
    async def opkg_install(package_name: str) -> dict[str, Any]:
        """
        Install a package using opkg.
        
        Args:
            package_name: Name of the package to install
            
        Returns:
            dict: Operation result
        """
        # Validate package name (alphanumeric, dash, underscore, dot)
        if not re.match(r'^[a-zA-Z0-9._-]+$', package_name):
            return {
                "success": False,
                "error": "Invalid package name. Use only alphanumeric characters, dash, underscore, and dot.",
            }

        command = f"opkg install {package_name}"
        result = await OpenWRTTools.execute_command(command)

        if result["success"]:
            return {
                "success": True,
                "message": f"Package '{package_name}' installed successfully",
                "output": result["output"],
            }
        else:
            return {
                "success": False,
                "error": f"Failed to install package '{package_name}': {result['error']}",
                "output": result["output"],
            }

    @staticmethod
    async def opkg_remove(package_name: str) -> dict[str, Any]:
        """
        Remove a package using opkg.
        
        Args:
            package_name: Name of the package to remove
            
        Returns:
            dict: Operation result
        """
        # Validate package name
        if not re.match(r'^[a-zA-Z0-9._-]+$', package_name):
            return {
                "success": False,
                "error": "Invalid package name. Use only alphanumeric characters, dash, underscore, and dot.",
            }

        command = f"opkg remove {package_name}"
        result = await OpenWRTTools.execute_command(command)

        if result["success"]:
            return {
                "success": True,
                "message": f"Package '{package_name}' removed successfully",
                "output": result["output"],
            }
        else:
            return {
                "success": False,
                "error": f"Failed to remove package '{package_name}': {result['error']}",
                "output": result["output"],
            }

    @staticmethod
    async def opkg_list_installed() -> dict[str, Any]:
        """
        List all installed packages.
        
        Returns:
            dict: List of installed packages
        """
        command = "opkg list-installed"
        result = await OpenWRTTools.execute_command(command)

        if result["success"]:
            # Parse package list
            packages = []
            for line in result["output"].strip().split("\n"):
                if line:
                    parts = line.split(" - ")
                    if len(parts) >= 2:
                        packages.append({
                            "name": parts[0],
                            "version": parts[1],
                        })

            return {
                "success": True,
                "packages": packages,
                "count": len(packages),
            }
        else:
            return {
                "success": False,
                "error": result["error"],
            }

    @staticmethod
    async def opkg_info(package_name: str) -> dict[str, Any]:
        """
        Get information about a package.
        
        Args:
            package_name: Name of the package
            
        Returns:
            dict: Package information
        """
        # Validate package name
        if not re.match(r'^[a-zA-Z0-9._-]+$', package_name):
            return {
                "success": False,
                "error": "Invalid package name. Use only alphanumeric characters, dash, underscore, and dot.",
            }

        command = f"opkg info {package_name}"
        result = await OpenWRTTools.execute_command(command)

        if result["success"]:
            # Parse package info
            info = {}
            for line in result["output"].strip().split("\n"):
                if ": " in line:
                    key, value = line.split(": ", 1)
                    info[key.lower().replace(" ", "_")] = value

            return {
                "success": True,
                "package_info": info,
            }
        else:
            return {
                "success": False,
                "error": result["error"],
                "output": result["output"],
            }

    @staticmethod
    async def opkg_list_available() -> dict[str, Any]:
        """
        List all available packages from repositories.
        
        Returns:
            dict: List of available packages
        """
        command = "opkg list"
        result = await OpenWRTTools.execute_command(command)

        if result["success"]:
            # Parse package list (can be very large)
            packages = []
            lines = result["output"].strip().split("\n")
            
            for line in lines[:500]:  # Limit to first 500 packages to avoid huge responses
                if line:
                    parts = line.split(" - ")
                    if len(parts) >= 2:
                        packages.append({
                            "name": parts[0],
                            "version": parts[1],
                            "description": parts[2] if len(parts) > 2 else "",
                        })

            total_lines = len(result["output"].strip().split("\n"))
            truncated = total_lines > 500

            return {
                "success": True,
                "packages": packages,
                "count": len(packages),
                "truncated": truncated,
                "total_available": total_lines,
                "note": "List limited to 500 packages. Use opkg_info to search for specific packages." if truncated else "",
            }
        else:
            return {
                "success": False,
                "error": result["error"],
            }
