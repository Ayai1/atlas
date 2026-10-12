"""Read-only view of the network connection.

Nothing in this module changes anything. It asks PowerShell for typed values
(connectivity, addresses, DNS servers) and asks `netsh` for Wi-Fi signal
strength, which PowerShell does not expose. The netsh part is best effort:
its labels are localised, so on a non-English Windows the Wi-Fi details are
simply left out rather than guessed.
"""

from __future__ import annotations

import json
import platform
import re
import subprocess
from dataclasses import dataclass, field


class NetworkError(RuntimeError):
    """The network state could not be read."""


# Windows' own judgement of each connection (NLM_CONNECTIVITY, simplified).
CONNECTIVITY = {
    0: "disconnected",
    1: "connected, but no traffic is getting through",
    2: "connected to this network only",
    3: "connected to this network only",
    4: "connected to the internet",
}
CATEGORY = {0: "Public", 1: "Private", 2: "Work domain"}

_SCRIPT = r"""
$profiles = @(Get-NetConnectionProfile -ErrorAction SilentlyContinue |
  Select-Object InterfaceAlias, Name,
    @{n='Connectivity';e={[int]$_.IPv4Connectivity}},
    @{n='Category';e={[int]$_.NetworkCategory}})
$configs = @(Get-NetIPConfiguration -ErrorAction SilentlyContinue |
  Where-Object { $_.NetAdapter.Status -eq 'Up' } |
  Select-Object InterfaceAlias,
    @{n='IPv4';e={@($_.IPv4Address | ForEach-Object { $_.IPAddress })}},
    @{n='Gateway';e={@($_.IPv4DefaultGateway | ForEach-Object { $_.NextHop })}},
    @{n='Dns';e={@($_.DNSServer | Where-Object { $_.AddressFamily -eq 2 } |
                   ForEach-Object { $_.ServerAddresses })}})
@{ profiles = $profiles; configs = $configs } | ConvertTo-Json -Depth 4
"""


@dataclass
class Connection:
    name: str                       # adapter, e.g. "Wi-Fi"
    network: str = ""               # network name Windows shows
    connectivity: int | None = None
    category: int | None = None
    ipv4: list[str] = field(default_factory=list)
    gateway: list[str] = field(default_factory=list)
    dns: list[str] = field(default_factory=list)


@dataclass
class Wifi:
    ssid: str
    signal: int | None              # percent
    band: str = ""
    rate_mbps: int | None = None


def _run(args: list[str]) -> str:
    if platform.system() != "Windows":
        raise NetworkError(
            f"This reads Windows networking; this machine reports "
            f"'{platform.system()}'."
        )
    try:
        proc = subprocess.run(
            args, capture_output=True, text=True, check=False, timeout=30,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise NetworkError(f"Could not run {args[0]}: {exc}") from exc
    return proc.stdout


def _as_list(value) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def parse_connections(raw: str) -> list[Connection]:
    """Turn the PowerShell JSON into one Connection per active adapter."""
    try:
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as exc:
        raise NetworkError(f"Could not understand the network details: {exc}") from exc

    found: dict[str, Connection] = {}
    for c in _as_list(data.get("configs")):
        alias = c.get("InterfaceAlias", "?")
        found[alias] = Connection(
            name=alias,
            ipv4=[str(x) for x in _as_list(c.get("IPv4"))],
            gateway=[str(x) for x in _as_list(c.get("Gateway"))],
            dns=[str(x) for x in _as_list(c.get("Dns"))],
        )
    for p in _as_list(data.get("profiles")):
        alias = p.get("InterfaceAlias", "?")
        conn = found.setdefault(alias, Connection(name=alias))
        conn.network = p.get("Name") or ""
        conn.connectivity = p.get("Connectivity")
        conn.category = p.get("Category")
    return list(found.values())


def parse_wifi(text: str) -> Wifi | None:
    """English `netsh wlan show interfaces` only; None when it cannot tell."""
    def field_(label: str) -> str | None:
        m = re.search(rf"^\s*{label}\s*:\s*(.+?)\s*$", text, re.MULTILINE)
        return m.group(1) if m else None

    ssid = field_("SSID")
    if not ssid:
        return None
    signal = field_("Signal")
    rate = field_(r"Receive rate \(Mbps\)")
    return Wifi(
        ssid=ssid,
        signal=int(signal.rstrip("%")) if signal and signal.rstrip("%").isdigit() else None,
        band=field_("Band") or "",
        rate_mbps=int(float(rate)) if rate and rate.replace(".", "").isdigit() else None,
    )


def read_connections() -> list[Connection]:
    return parse_connections(_run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", _SCRIPT]))


def read_wifi() -> Wifi | None:
    try:
        return parse_wifi(_run(["netsh", "wlan", "show", "interfaces"]))
    except NetworkError:
        return None
