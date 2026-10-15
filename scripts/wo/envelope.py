"""The structured CLI envelope every command returns.

Required by the shared authoring guide. It exists so calling agents parse a
document instead of scraping text: `action` names what was attempted, `state`
names where it landed, `data` carries the payload, `error` carries the reason.
"""

from __future__ import annotations

import json
import sys
from typing import Any

ENVELOPE_KEYS = ("action", "success", "state", "message", "data", "error")

# State values used across the skill. The full set lives in the run manifest
# standard; these are the ones this skill can actually produce.
STATES = ("Succeeded", "Partial", "Failed", "Blocked", "DryRun")


def envelope(
    action: str,
    success: bool,
    state: str,
    message: str,
    data: Any = None,
    error: Any = None,
) -> dict[str, Any]:
    """Build an envelope. `state` is validated so typos fail loudly here."""
    if state not in STATES:
        raise ValueError(f"Unknown state {state!r}; expected one of {STATES}")
    return {
        "action": action,
        "success": success,
        "state": state,
        "message": message,
        "data": data,
        "error": error,
    }


def emit(result: dict[str, Any], as_json: bool, stream=None) -> None:
    """Print an envelope, or a short human summary when not in JSON mode."""
    stream = stream or sys.stdout
    if as_json:
        print(json.dumps(result, indent=2, ensure_ascii=False), file=stream)
        return
    print(f"{result['state']}: {result['message']}", file=stream)
    if not result["success"] and result["error"]:
        print(f"  {result['error']}", file=stream)


def failure(action: str, message: str, error: Any, state: str = "Failed") -> dict[str, Any]:
    return envelope(action, success=False, state=state, message=message, data=None, error=error)


def reconfigure_stdio() -> None:
    """Force UTF-8 on stdout/stderr so non-ASCII titles do not raise."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass