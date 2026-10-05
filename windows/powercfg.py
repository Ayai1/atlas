"""Thin wrapper around Windows `powercfg`.

The only place power settings are actually touched. Two facts about powercfg
that this module exists to hide:

1. `/query` reports values in HEX SECONDS, while `/change` takes MINUTES.
2. `/query` output is LOCALISED. On a non-English Windows the label
   "Current AC Power Setting Index" does not appear, so we parse by label
   first and fall back to positional parsing of the hex values, whose order
   is stable across locales.

Long term the typed PowerShell/WMI route is better than scraping CLI text.
See ARCHITECTURE.md section 12.
"""

from __future__ import annotations

import platform
import re
import subprocess
from dataclasses import dataclass

# Timeout settings we support, mapped to their query subgroup/setting aliases
# and their `/change` names.
TIMEOUTS = {
    "monitor": {
        "subgroup": "SUB_VIDEO",
        "setting": "VIDEOIDLE",
        "change_ac": "monitor-timeout-ac",
        "change_dc": "monitor-timeout-dc",
        "label": "screen turning off",
    },
    "standby": {
        "subgroup": "SUB_SLEEP",
        "setting": "STANDBYIDLE",
        "change_ac": "standby-timeout-ac",
        "change_dc": "standby-timeout-dc",
        "label": "the computer going to sleep",
    },
}


class PowercfgError(RuntimeError):
    """powercfg was unavailable, refused, or returned something unparseable."""


@dataclass
class Timeouts:
    """Minutes of idle time. 0 means never."""

    ac: int   # plugged in
    dc: int   # on battery


def _require_windows() -> None:
    if platform.system() != "Windows":
        raise PowercfgError(
            f"powercfg is a Windows tool; this machine reports "
            f"'{platform.system()}'. Power settings can only be changed on Windows."
        )


def _run(args: list[str]) -> str:
    _require_windows()
    try:
        proc = subprocess.run(
            args, capture_output=True, text=True, check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except FileNotFoundError as exc:
        raise PowercfgError("powercfg.exe was not found on this system.") from exc
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip() or "no output"
        if "privilege" in detail.lower() or "denied" in detail.lower():
            raise PowercfgError(
                f"Windows refused this change: {detail}\n"
                "This setting needs an administrator command prompt."
            )
        raise PowercfgError(
            f"'{' '.join(args)}' failed (exit {proc.returncode}): {detail}"
        )
    return proc.stdout


def _parse_indices(output: str) -> tuple[int, int]:
    """Extract (AC, DC) setting indices in seconds from `powercfg /query` text.

    Tries the English labels first, then falls back to position. In the
    fallback, the hex values appear in a fixed order regardless of language,
    and the AC and DC indices are always the last two. A numeric setting
    prints minimum, maximum and increment before them; a choice setting
    prints its options as plain "000", "001", so it has only the two.
    """
    ac = re.search(r"Current AC Power Setting Index:\s*(0x[0-9a-fA-F]+)", output)
    dc = re.search(r"Current DC Power Setting Index:\s*(0x[0-9a-fA-F]+)", output)
    if ac and dc:
        return int(ac.group(1), 16), int(dc.group(1), 16)

    hexes = re.findall(r"0x[0-9a-fA-F]{8}", output)
    if len(hexes) >= 2:
        return int(hexes[-2], 16), int(hexes[-1], 16)

    raise PowercfgError(
        "Could not read the current value from powercfg output. "
        "This can happen on a non-English Windows install.\n"
        f"Output was:\n{output.strip()[:400]}"
    )


def _seconds_to_minutes(seconds: int) -> int:
    """powercfg stores seconds; the CLI speaks minutes.

    Values are always whole minutes in practice. A sub-minute value would
    truncate, so round rather than floor to avoid reporting 0 for 30s.
    """
    return (seconds + 30) // 60 if seconds else 0


def read_timeouts(kind: str) -> Timeouts:
    """Current idle timeout in minutes for 'monitor' or 'standby'."""
    if kind not in TIMEOUTS:
        raise PowercfgError(f"Unknown timeout '{kind}'")
    spec = TIMEOUTS[kind]
    out = _run(["powercfg", "/query", "SCHEME_CURRENT",
                spec["subgroup"], spec["setting"]])
    ac_s, dc_s = _parse_indices(out)
    return Timeouts(ac=_seconds_to_minutes(ac_s), dc=_seconds_to_minutes(dc_s))


def change_command(kind: str, minutes: int, on_battery: bool = False) -> list[str]:
    """The exact command that will run. Built separately so preview and
    execute can never disagree about what is about to happen."""
    spec = TIMEOUTS[kind]
    key = spec["change_dc"] if on_battery else spec["change_ac"]
    return ["powercfg", "/change", key, str(minutes)]


def write_timeout(kind: str, minutes: int, on_battery: bool = False) -> str:
    """Set the timeout. Returns the command that was run."""
    if kind not in TIMEOUTS:
        raise PowercfgError(f"Unknown timeout '{kind}'")
    cmd = change_command(kind, minutes, on_battery)
    _run(cmd)
    return " ".join(cmd)


def active_scheme() -> str:
    """Human-readable name of the active power plan, e.g. 'Balanced'."""
    out = _run(["powercfg", "/getactivescheme"])
    m = re.search(r"\(([^)]+)\)\s*$", out.strip())
    return m.group(1) if m else out.strip()


# ---- any setting inside a power plan ---------------------------------
#
# Most power settings live inside the active power plan and are reachable
# only through Control Panel's "Change advanced power settings" dialog.
# They are all read and written the same way, so one pair of functions
# covers every one of them.
#
# Reads use /qh rather than /query. /query silently prints nothing for a
# setting Windows has marked hidden (the lid action on a desktop, the wake
# password, ...) and still exits 0. /qh prints hidden settings too.

_GUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"


@dataclass
class PlanValue:
    """A setting's value in one power plan. Raw indices, as Windows stores them."""

    scheme: str   # GUID of the plan it was read from
    ac: int       # plugged in
    dc: int       # on battery


def parse_plan_value(output: str) -> PlanValue:
    """Parse `powercfg /qh SCHEME_CURRENT <subgroup> <setting>` output."""
    guids = re.findall(_GUID, output)
    if not guids:
        raise PowercfgError(
            f"Could not tell which power plan is active.\nOutput was:\n"
            f"{output.strip()[:400]}"
        )
    # Only the scheme line and its alias: the setting itself was not printed.
    if len(guids) < 3:
        raise PowercfgError(
            "This computer's power plan does not have that setting. Some "
            "settings only exist on laptops, or on particular hardware."
        )
    ac, dc = _parse_indices(output)
    return PlanValue(scheme=guids[0].lower(), ac=ac, dc=dc)


def read_plan_value(subgroup: str, setting: str) -> PlanValue:
    """Current AC and DC index of one setting in the active plan."""
    try:
        out = _run(["powercfg", "/qh", "SCHEME_CURRENT", subgroup, setting])
    except PowercfgError as exc:
        if "does not exist" in str(exc):
            raise PowercfgError(
                "This computer's power plan does not have that setting. Some "
                "settings only exist on laptops, or on particular hardware."
            ) from exc
        raise
    return parse_plan_value(out)


def plan_value_commands(
    subgroup: str, setting: str, *, ac: int | None = None,
    dc: int | None = None, scheme: str = "SCHEME_CURRENT",
) -> list[list[str]]:
    """The exact commands that will run, built once so preview and execute
    cannot disagree.

    Values are written to a named plan. The final /setactive re-applies the
    active plan, which is what makes Windows pick the new value up now
    rather than at the next plan switch.
    """
    cmds = []
    if ac is not None:
        cmds.append(["powercfg", "/setacvalueindex", scheme, subgroup,
                     setting, str(ac)])
    if dc is not None:
        cmds.append(["powercfg", "/setdcvalueindex", scheme, subgroup,
                     setting, str(dc)])
    cmds.append(["powercfg", "/setactive", "SCHEME_CURRENT"])
    return cmds


def join_commands(cmds: list[list[str]]) -> str:
    return " && ".join(" ".join(c) for c in cmds)


def write_plan_value(
    subgroup: str, setting: str, *, ac: int | None = None,
    dc: int | None = None, scheme: str = "SCHEME_CURRENT",
) -> str:
    """Set one setting's AC and/or DC index. Returns the commands run."""
    cmds = plan_value_commands(subgroup, setting, ac=ac, dc=dc, scheme=scheme)
    for cmd in cmds:
        _run(cmd)
    return join_commands(cmds)


# ---- choosing the power plan itself ----------------------------------

@dataclass
class Plan:
    guid: str
    name: str
    active: bool


def parse_plan_list(output: str) -> list[Plan]:
    """Parse `powercfg /list`. One plan per line; the active one ends in '*'."""
    plans = []
    for line in output.splitlines():
        # Greedy, so a plan named "Work (copy)" keeps its own brackets.
        m = re.search(rf"({_GUID})\s+\((.*)\)\s*(\*)?\s*$", line)
        if m:
            plans.append(Plan(guid=m.group(1).lower(), name=m.group(2),
                              active=bool(m.group(3))))
    if not plans:
        raise PowercfgError(
            f"Could not read the list of power plans.\nOutput was:\n"
            f"{output.strip()[:400]}"
        )
    return plans


def list_plans() -> list[Plan]:
    return parse_plan_list(_run(["powercfg", "/list"]))


def set_active_command(guid: str) -> list[str]:
    return ["powercfg", "/setactive", guid]


def set_active_plan(guid: str) -> str:
    cmd = set_active_command(guid)
    _run(cmd)
    return " ".join(cmd)
