"""Screen brightness, through WMI.

The only place brightness is touched. WMI exposes brightness for screens the
computer drives directly: a laptop's built-in panel, and some all-in-ones.
External monitors usually do not report brightness to Windows at all; their
own buttons control it. We say so rather than pretending.

PowerShell's CIM cmdlets return typed numbers, so unlike powercfg there is no
localised text to parse.
"""

from __future__ import annotations

import platform
import subprocess


class DisplayError(RuntimeError):
    """Brightness could not be read or changed."""


_READ = ("(Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBrightness "
         "-ErrorAction Stop | Select-Object -First 1).CurrentBrightness")

_NOT_SUPPORTED = (
    "Windows cannot control this screen's brightness. That is normal for an "
    "external monitor: use the buttons on the monitor itself."
)


def _powershell(script: str) -> str:
    if platform.system() != "Windows":
        raise DisplayError(
            f"Brightness can only be changed on Windows; this machine reports "
            f"'{platform.system()}'."
        )
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, check=False, timeout=20,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise DisplayError(f"Could not run PowerShell: {exc}") from exc
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        # Only a screen WMI does not know about means "not supported". Any
        # other failure is shown as it is, so a real bug is not disguised.
        if "not supported" in detail.lower() or "No instances" in detail:
            raise DisplayError(_NOT_SUPPORTED)
        raise DisplayError(f"PowerShell failed: {detail[:300] or 'no output'}")
    return proc.stdout.strip()


def read_brightness() -> int:
    """Current brightness, 0-100."""
    out = _powershell(_READ)
    try:
        return int(out.splitlines()[-1])
    except (IndexError, ValueError):
        raise DisplayError(_NOT_SUPPORTED) from None


def brightness_command(percent: int) -> str:
    """The exact command that will run, shown on the confirmation card.

    WmiSetBrightness is an instance method, so it is called on the monitor
    object rather than the class, and WMI insists on exact types: Brightness
    is a byte and Timeout a uint32. A plain integer fails with "Type mismatch".
    """
    return ("Get-CimInstance -Namespace root/wmi -ClassName "
            "WmiMonitorBrightnessMethods | Invoke-CimMethod -MethodName "
            f"WmiSetBrightness -Arguments @{{Brightness=[byte]{int(percent)}; "
            "Timeout=[uint32]0}")


def write_brightness(percent: int) -> str:
    cmd = brightness_command(percent)
    _powershell(cmd + " | Out-Null")
    return cmd
