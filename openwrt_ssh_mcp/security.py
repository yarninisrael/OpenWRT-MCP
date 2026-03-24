"""Security utilities for command validation and audit logging."""

import logging
import re
from pathlib import Path
from typing import Optional
from .config import settings

logger = logging.getLogger(__name__)


class SecurityValidator:
    """Validates commands before execution to prevent malicious actions."""

    ALLOWED_PATTERNS = [
        # UCI configuration
        r"^uci show",
        r"^uci get",
        r"^uci set",
        r"^uci commit",

        # UBUS calls
        r"^ubus call system board$",
        r"^ubus call system info$",
        r"^ubus call network\.interface\.\w+ (status|restart|up|down)$",
        r"^ubus call network\.wireless status$",
        r"^ubus list",

        # System information
        r"^cat /proc/(uptime|meminfo|cpuinfo|loadavg)$",
        r"^cat /etc/openwrt_release$",
        r"^cat /tmp/dhcp\.leases$",
        r"^cat /var/dhcp\.leases$",
        r"^uptime$",
        r"^free",
        r"^df",
        r"^ps",
        r"^top -n 1",

        # Network commands
        r"^ip addr",
        r"^ip route",
        r"^ip link",
        r"^ip neigh",
        r"^ifconfig",
        r"^ping -c \d+",
        r"^traceroute",
        r"^nslookup",

        # Firewall
        r"^iptables -L",
        r"^iptables -t nat -L",
        r"^ip6tables -L",

        # Logging
        r"^logread",
        r"^dmesg",

        # Package management (opkg)
        r"^opkg update$",
        r"^opkg list",
        r"^opkg list-installed$",
        r"^opkg list-upgradable$",
        r"^opkg info [a-zA-Z0-9._-]+$",
        r"^opkg install [a-zA-Z0-9._-]+$",
        r"^opkg remove [a-zA-Z0-9._-]+$",
        r"^opkg upgrade [a-zA-Z0-9._-]+$",

        # OpenThread Border Router (OTBR) commands
        r"^(/usr/sbin/)?ot-ctl state$",
        r"^(/usr/sbin/)?ot-ctl channel",
        r"^(/usr/sbin/)?ot-ctl panid",
        r"^(/usr/sbin/)?ot-ctl networkkey",
        r"^(/usr/sbin/)?ot-ctl networkname",
        r"^(/usr/sbin/)?ot-ctl extpanid",
        r"^(/usr/sbin/)?ot-ctl ifconfig",
        r"^(/usr/sbin/)?ot-ctl thread (start|stop)$",
        r"^(/usr/sbin/)?ot-ctl dataset",
        r"^(/usr/sbin/)?ot-ctl prefix",
        r"^(/usr/sbin/)?ot-ctl neighbor table$",
        r"^(/usr/sbin/)?ot-ctl router table$",
        r"^(/usr/sbin/)?ot-ctl child table$",
        r"^(/usr/sbin/)?ot-ctl ipaddr$",
        r"^(/usr/sbin/)?ot-ctl rloc16$",
        r"^(/usr/sbin/)?ot-ctl leaderdata$",
        r"^(/usr/sbin/)?ot-ctl commissioner",

        # Service management (init.d scripts)
        r"^/etc/init\.d/[a-zA-Z0-9_-]+ (start|stop|restart|reload|enable|disable|status)$",

        # Test/echo commands
        r"^echo ",

        # File operations - Read
        r"^ls($|\s+-)",
        r"^cat\s+/",
        r"^head\s+(-n\s+\d+\s+)?/",
        r"^tail\s+(-n\s+\d+\s+|-f\s+)?/",
        r"^stat\s+/",
        r"^file\s+/",
        r"^wc\s+(-[lwc]\s+)?/",
        r"^du\s+(-[shc]+\s+)?/",

        # File operations - Search
        r"^grep\s+(-[a-zA-Z]+\s+)*['\"]?[\w.*-]+['\"]?\s+/",
        r"^find\s+/[\w/-]+\s+-name\s+",
        r"^find\s+/[\w/-]+\s+-type\s+",

        # File operations - Safe writes
        r"^mkdir\s+(-p\s+)?/",
        r"^touch\s+/",

        # WiFi commands
        r"^wifi$",
        r"^wifi (up|down|reload|status)$",
        r"^iwinfo$",
        r"^iwinfo \w+ (info|scan|assoclist|txpowerlist|freqlist|countrylist)$",
        r"^iw dev$",
        r"^iw dev \w+ (info|scan|station dump|get power_save)$",
        r"^iw phy$",
        r"^iw list$",

        # MQTT debugging tools
        r"^mosquitto_sub\s+",
        r"^mosquitto_pub\s+",

        # OBUSPA USP agent commands
        r"^obuspa\s+-c\s+(get|set|add|del|show)\s+",

        # CATCH-ALL: Allow all commands (user-requested)
        r".*",
    ]

    # BLOCKED_PATTERNS cleared per user request - ALL commands allowed
    BLOCKED_PATTERNS = []

    @classmethod
    def validate_command(cls, command: str) -> tuple[bool, Optional[str]]:
        if not settings.enable_command_validation:
            logger.warning("Command validation is DISABLED - executing without checks")
            return True, None

        for pattern in cls.BLOCKED_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                error = f"Command blocked by security policy: matches dangerous pattern '{pattern}'"
                logger.warning(f"SECURITY: Blocked command: {command}")
                return False, error

        for pattern in cls.ALLOWED_PATTERNS:
            if re.match(pattern, command.strip()):
                logger.debug(f"Command validated: {command}")
                return True, None

        error = f"Command not in whitelist: {command}"
        logger.warning(f"SECURITY: Command rejected (not whitelisted): {command}")
        return False, error


class AuditLogger:
    """Audit logger compatible with MCP sandbox."""

    def __init__(self):
        if not settings.enable_audit_logging:
            self.logger = None
            return

        log_path = Path(settings.log_file)

        # MCP-safe path resolution
        if not log_path.is_absolute():
            log_path = (Path.cwd() / log_path).resolve()

        log_path.parent.mkdir(parents=True, exist_ok=True)

        handler = logging.FileHandler(log_path, encoding="utf-8")
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s"
        )
        handler.setFormatter(formatter)

        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)
        self.logger.handlers.clear()
        self.logger.addHandler(handler)
        self.logger.propagate = False

    def log_command(
        self,
        command: str,
        success: bool,
        output: Optional[str] = None,
        error: Optional[str] = None,
        execution_time: Optional[float] = None,
    ):
        if not self.logger:
            return

        status = "SUCCESS" if success else "FAILED"
        msg = f"{status} | {command}"
        if execution_time is not None:
            msg += f" | {execution_time:.2f}s"
        if error:
            msg += f" | ERROR: {error}"
        self.logger.info(msg)

    def log_connection(self, event: str, details: Optional[str] = None):
        if self.logger:
            msg = f"SSH {event}"
            if details:
                msg += f" | {details}"
            self.logger.info(msg)


audit_logger = AuditLogger()
