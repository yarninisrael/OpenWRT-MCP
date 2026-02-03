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
        r"^uci show",
        r"^uci get",
        r"^ip addr",
        r"^ip route",
        r"^logread",
        r"^dmesg",
        r"^opkg list",
        r"^opkg update",
    ]

    BLOCKED_PATTERNS = [
        r"rm\s+-rf",
        r"mkfs",
        r"dd\s+if=",
        r"shutdown",
        r"reboot",
        r"halt",
        r"poweroff",
        r"^passwd\b",
    ]

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
