"""Network: what the connection is doing, and the proxy switch.

Most network settings (DNS servers, network profile, adapter options) need
administrator rights, and wait for elevation handling. These two do not.
`network.status` is read-only and answers the question people actually ask,
"is it my computer or the internet?", in plain language.
"""

from __future__ import annotations

from typing import Any

from engine.tool import Safety, Tool, ToolResult
from tools.registry_choice import RegistryChoiceTool
from windows import network
from windows import winsettings as ws


def _signal_words(percent: int) -> str:
    if percent >= 75:
        return "strong"
    if percent >= 50:
        return "fair"
    if percent >= 30:
        return "weak; moving closer to the router should help"
    return "very weak, which by itself can make the internet slow or drop out"


class NetworkStatusTool(Tool):
    name = "network.status"
    category = "network"
    description = ("Whether this computer is connected to the internet, and "
                   "how well")
    safety = Safety.READ_ONLY
    keywords = [
        "internet", "connected", "connection", "offline", "online", "wifi",
        "wi fi", "network", "not working", "no internet", "signal", "router",
        "slow", "ip", "dns", "is it me",
    ]

    def execute(self, **kwargs: Any) -> ToolResult:
        self.validate(**kwargs)
        conns = network.read_connections()
        wifi = network.read_wifi()
        proxy_on = ws.read_value(ws.PROXY_ENABLE) == 1

        data: dict[str, Any] = {}
        lines: list[str] = []

        if not conns:
            lines.append("This computer is not connected to any network. "
                         "Check that Wi-Fi is on, or that the cable is "
                         "plugged in.")
        online = False
        for c in conns:
            state = network.CONNECTIVITY.get(c.connectivity, "state unknown")
            online = online or c.connectivity == 4
            data[f"{c.name} connection"] = state
            if c.ipv4:
                data[f"{c.name} address"] = ", ".join(c.ipv4)
            if c.dns:
                data[f"{c.name} DNS"] = ", ".join(c.dns)
            if c.category is not None:
                data[f"{c.name} profile"] = network.CATEGORY.get(c.category, "?")

        if wifi:
            data["Wi-Fi network"] = wifi.ssid
            if wifi.signal is not None:
                data["Signal"] = f"{wifi.signal}%"
            if wifi.band:
                data["Band"] = wifi.band
        data["Proxy"] = "on" if proxy_on else "off"

        if conns:
            if online:
                lines.append("Windows says this computer can reach the "
                             "internet. If a website will not load, the "
                             "problem is more likely that website, or the "
                             "browser, than this computer.")
            elif any(c.gateway for c in conns):
                lines.append("This computer is connected to the router, but "
                             "Windows cannot reach the internet through it. "
                             "Restarting the router usually fixes this, and "
                             "if not, the problem is with the provider.")
            else:
                lines.append("A network adapter is on, but it has no route to "
                             "a router. Reconnecting to the Wi-Fi, or "
                             "re-plugging the cable, is the first thing to try.")
        if wifi and wifi.signal is not None:
            lines.append(f"The Wi-Fi signal is {wifi.signal}%, which is "
                         f"{_signal_words(wifi.signal)}.")
        if any(c.category == 0 for c in conns):
            lines.append("The network is marked Public, so other devices on "
                         "it cannot see this computer. That is the safe "
                         "choice for cafés and hotels.")
        if proxy_on:
            lines.append("A proxy is switched on. If you did not set one up, "
                         "it may be why some sites fail to load: "
                         "'atlas show network.proxy'.")

        return ToolResult(
            title="Network Status",
            data=data,
            explanation=" ".join(lines),
        )


class ProxyTool(RegistryChoiceTool):
    name = "network.proxy"
    category = "network"
    description = ("Whether web traffic is sent through a manually set "
                   "proxy server")
    result_title = "Manual proxy"
    setting = ws.PROXY_ENABLE
    labels = {0: ("off", "off (connect directly)"),
              1: ("on", "on (send traffic through the proxy)")}
    choice_hint = "Use the manually set proxy server, or connect directly."
    where = "Settings, then Network & internet, then Proxy"
    keywords = [
        "proxy", "websites", "web pages", "not loading", "pages wont load",
        "browser", "cant connect", "internet", "blocked", "hijacked",
        "malware", "redirect",
    ]

    def server(self) -> str | None:
        return ws.read_text(ws.INTERNET_SETTINGS, "ProxyServer")

    def describe(self, raw: int) -> str:
        if raw == 1:
            server = self.server()
            return f"on (through {server})" if server else "on"
        return super().describe(raw)

    def check(self, raw: int) -> None:
        if raw == 1 and not self.server():
            raise ValueError(
                f"{self.name}: no proxy server address is saved on this "
                "computer, so there is nothing to switch on. Atlas only "
                "turns an existing proxy on or off; it never sets the address."
            )

    def meaning(self, raw: int) -> str:
        if raw == 0:
            return ("If a program or browser extension switched a proxy on "
                    "without asking, this is a common reason pages stopped "
                    "loading. The saved address is kept, so turning it back on "
                    "restores it. Automatic proxy setup scripts are separate "
                    "and are not changed.")
        return ""


ALL_NETWORK_TOOLS = [NetworkStatusTool, ProxyTool]
