"""Display, network and storage — every change round-trips; reports explain."""

from collections import namedtuple

import pytest

from engine import executor
from tests.conftest import BALANCED
from tools.display.settings import (
    ALL_DISPLAY_TOOLS, AdaptiveBrightnessTool, AppThemeTool, BrightnessTool,
    TransparencyTool, WindowsThemeTool,
)
from tools.network.settings import ALL_NETWORK_TOOLS, NetworkStatusTool, ProxyTool
from tools.storage.settings import (
    ALL_STORAGE_TOOLS, DiskUsageTool, RecycleBinCleanupTool,
    StorageSenseScheduleTool, StorageSenseTool, TempFilesCleanupTool,
)
from windows import display, network
from windows import winsettings as ws


@pytest.fixture
def fake_brightness(monkeypatch):
    state = {"percent": 20, "commands": []}

    def write(p):
        state["percent"] = p
        cmd = display.brightness_command(p)
        state["commands"].append(cmd)
        return cmd

    monkeypatch.setattr(display, "read_brightness", lambda: state["percent"])
    monkeypatch.setattr(display, "write_brightness", write)
    return state


# (tool, value different from the fake's start, setting it writes)
REGISTRY_CHOICES = [
    (AppThemeTool, "light", ws.APPS_LIGHT),
    (WindowsThemeTool, "light", ws.SYSTEM_LIGHT),
    (TransparencyTool, "off", ws.TRANSPARENCY),
    (StorageSenseTool, "off", ws.STORAGE_SENSE),
    (StorageSenseScheduleTool, "every_week", ws.STORAGE_SENSE_SCHEDULE),
    (TempFilesCleanupTool, "off", ws.STORAGE_SENSE_TEMP),
    (RecycleBinCleanupTool, "60_days", ws.STORAGE_SENSE_RECYCLE_DAYS),
]


def _stored(fake, setting):
    return fake.values.get((setting.key, setting.name))


class TestRegistryChoicesRoundTrip:
    @pytest.mark.parametrize("cls,target,setting", REGISTRY_CHOICES)
    def test_change_then_undo_restores_the_registry_exactly(
        self, cls, target, setting, fake_registry, journal, always_yes
    ):
        before = _stored(fake_registry, setting)
        tool = cls()
        executor.run(tool, {"value": target}, journal, confirm=always_yes)
        assert _stored(fake_registry, setting) == tool.to_raw(target)

        tool.undo(journal.last_undoable().prior)
        assert _stored(fake_registry, setting) == before   # None stays None

    @pytest.mark.parametrize("cls,target,setting", REGISTRY_CHOICES)
    def test_preview_matches_what_runs(self, cls, target, setting, fake_registry):
        tool = cls()
        preview = tool.preview(value=target)
        assert preview.command == tool.execute(value=target).command_run
        assert preview.reversible and preview.summary

    def test_absent_value_is_labelled_as_the_windows_default(self, fake_registry):
        preview = RecycleBinCleanupTool().preview(value="14_days")
        assert "Windows default" in preview.current_value
        assert "30 days" in preview.current_value

    def test_undo_removes_a_value_windows_never_had(
        self, fake_registry, journal, always_yes
    ):
        s = ws.STORAGE_SENSE_RECYCLE_DAYS
        executor.run(RecycleBinCleanupTool(), {"value": "1_day"}, journal,
                     confirm=always_yes)
        RecycleBinCleanupTool().undo(journal.last_undoable().prior)
        assert (s.key, s.name) not in fake_registry.values
        assert any(w.startswith("removed") for w in fake_registry.writes)

    @pytest.mark.parametrize("cls,bad", [
        (AppThemeTool, "purple"), (TransparencyTool, "1"),
        (StorageSenseScheduleTool, "every_hour"), (RecycleBinCleanupTool, "7_days"),
    ])
    def test_unknown_options_never_reach_the_registry(
        self, cls, bad, fake_registry, journal, always_yes
    ):
        writes = list(fake_registry.writes)
        with pytest.raises(ValueError):
            executor.run(cls(), {"value": bad}, journal, confirm=always_yes)
        assert fake_registry.writes == writes


class TestNoIrreversibleSideEffects:
    def test_recycle_bin_cleanup_warns_that_emptied_files_are_gone(self, fake_registry):
        result = RecycleBinCleanupTool().execute(value="14_days")
        assert any("gone for good" in w for w in result.warnings)

    def test_never_carries_no_warning(self, fake_registry):
        assert RecycleBinCleanupTool().execute(value="never").warnings == []

    def test_there_is_no_tool_that_deletes_downloads(self, registry):
        assert not any("download" in t.name for t in registry.all())


class TestBrightness:
    def test_round_trip(self, fake_brightness, fake_plans, journal, always_yes):
        tool = BrightnessTool()
        executor.run(tool, {"percent": 70}, journal, confirm=always_yes)
        assert fake_brightness["percent"] == 70
        tool.undo(journal.last_undoable().prior)
        assert fake_brightness["percent"] == 20

    @pytest.mark.parametrize("bad", [0, 5, 101])
    def test_cannot_go_dark_enough_to_hide_the_undo(
        self, bad, fake_brightness, journal, always_yes
    ):
        with pytest.raises(ValueError):
            executor.run(BrightnessTool(), {"percent": bad}, journal,
                         confirm=always_yes)
        assert fake_brightness["commands"] == []

    def test_warns_when_adaptive_brightness_will_fight_it(
        self, fake_brightness, fake_plans
    ):
        fake_plans.values[BALANCED][("SUB_VIDEO", "ADAPTBRIGHT")] = [1, 1]
        result = BrightnessTool().execute(percent=50)
        assert any("adaptive" in w for w in result.warnings)

    def test_adaptive_brightness_round_trips(self, fake_plans, journal, always_yes):
        tool = AdaptiveBrightnessTool()
        executor.run(tool, {"enabled": "on"}, journal, confirm=always_yes)
        assert fake_plans.values[BALANCED][("SUB_VIDEO", "ADAPTBRIGHT")] == [1, 1]
        tool.undo(journal.last_undoable().prior)
        assert fake_plans.values[BALANCED][("SUB_VIDEO", "ADAPTBRIGHT")] == [0, 0]


class TestProxy:
    KEY = (ws.INTERNET_SETTINGS, "ProxyServer")

    def test_refuses_to_switch_on_a_proxy_that_does_not_exist(
        self, fake_registry, journal, always_yes
    ):
        with pytest.raises(ValueError, match="no proxy server"):
            executor.run(ProxyTool(), {"value": "on"}, journal, confirm=always_yes)
        assert journal.last_undoable() is None

    def test_switching_off_keeps_the_address_so_undo_restores_it(
        self, fake_registry, journal, always_yes
    ):
        fake_registry.texts[self.KEY] = "10.0.0.5:8080"
        fake_registry.values[(ws.PROXY_ENABLE.key, ws.PROXY_ENABLE.name)] = 1
        tool = ProxyTool()
        assert "10.0.0.5:8080" in tool.preview(value="off").current_value

        executor.run(tool, {"value": "off"}, journal, confirm=always_yes)
        tool.undo(journal.last_undoable().prior)
        assert _stored(fake_registry, ws.PROXY_ENABLE) == 1
        assert fake_registry.texts[self.KEY] == "10.0.0.5:8080"


# ---- read-only reports ----------------------------------------------

def _conn(**kw):
    base = dict(name="Wi-Fi", network="Home", connectivity=4, category=1,
                ipv4=["192.168.0.10"], gateway=["192.168.0.1"],
                dns=["192.168.0.1"])
    base.update(kw)
    return network.Connection(**base)


@pytest.fixture
def fake_net(monkeypatch, fake_registry):
    state = {"conns": [_conn()], "wifi": network.Wifi("Home", 80, "5 GHz", 600)}
    monkeypatch.setattr(network, "read_connections", lambda: state["conns"])
    monkeypatch.setattr(network, "read_wifi", lambda: state["wifi"])
    return state


class TestNetworkStatus:
    def test_online(self, fake_net):
        r = NetworkStatusTool().execute()
        assert "can reach the internet" in r.explanation
        assert "strong" in r.explanation
        assert r.data["Wi-Fi connection"] == "connected to the internet"

    def test_router_but_no_internet_points_at_the_router(self, fake_net):
        fake_net["conns"] = [_conn(connectivity=3)]
        assert "Restarting the router" in NetworkStatusTool().execute().explanation

    def test_nothing_connected(self, fake_net):
        fake_net["conns"], fake_net["wifi"] = [], None
        assert "not connected to any network" in NetworkStatusTool().execute().explanation

    def test_weak_signal_is_called_out(self, fake_net):
        fake_net["wifi"] = network.Wifi("Home", 20)
        assert "very weak" in NetworkStatusTool().execute().explanation

    def test_unexpected_proxy_is_called_out(self, fake_net, fake_registry):
        fake_registry.values[(ws.PROXY_ENABLE.key, ws.PROXY_ENABLE.name)] = 1
        assert "proxy is switched on" in NetworkStatusTool().execute().explanation

    def test_changes_nothing(self, fake_net, fake_registry):
        NetworkStatusTool().execute()
        assert fake_registry.writes == []


PS_JSON = """{
    "profiles":  [{"InterfaceAlias": "Wi-Fi", "Name": "T2-1103",
                   "Connectivity": 4, "Category": 0}],
    "configs":  [{"InterfaceAlias": "Wi-Fi", "IPv4": "192.168.0.103",
                  "Gateway": "192.168.0.1", "Dns": ["192.168.0.1", "1.1.1.1"]}]
}"""

NETSH_WLAN = """
There is 1 interface on the system:

    Name                   : Wi-Fi
    State                  : connected
    SSID                   : T2-1103
    AP BSSID               : 78:8c:b5:5f:f3:aa
    Band                   : 5 GHz
    Receive rate (Mbps)    : 780
    Signal                 : 88%
"""


class TestNetworkParsing:
    def test_powershell_json_with_single_values_unwrapped(self):
        [c] = network.parse_connections(PS_JSON)
        assert c.ipv4 == ["192.168.0.103"]          # PowerShell unwraps 1-item arrays
        assert c.dns == ["192.168.0.1", "1.1.1.1"]
        assert (c.network, c.connectivity, c.category) == ("T2-1103", 4, 0)

    def test_empty_output_means_no_connections(self):
        assert network.parse_connections("") == []

    def test_wifi(self):
        w = network.parse_wifi(NETSH_WLAN)
        assert (w.ssid, w.signal, w.band, w.rate_mbps) == ("T2-1103", 88, "5 GHz", 780)

    def test_bssid_is_not_mistaken_for_ssid(self):
        assert network.parse_wifi("    AP BSSID : 78:8c:b5:5f:f3:aa\n") is None


Usage = namedtuple("Usage", "total used free percent")
Part = namedtuple("Part", "device mountpoint fstype opts")


@pytest.fixture
def fake_disks(monkeypatch):
    import psutil
    disks = {}
    monkeypatch.setattr(psutil, "disk_partitions", lambda all=False: [
        Part(m, m, "NTFS", "rw,fixed") for m in disks])
    monkeypatch.setattr(psutil, "disk_usage", lambda m: disks[m])
    return disks


class TestDiskUsage:
    GB = 1024 ** 3

    def test_plenty_of_space(self, fake_disks):
        fake_disks["C:\\"] = Usage(500 * self.GB, 200 * self.GB, 300 * self.GB, 40.0)
        assert "Nothing needs doing" in DiskUsageTool().execute().explanation

    def test_low_space_points_at_storage_sense(self, fake_disks):
        fake_disks["C:\\"] = Usage(256 * self.GB, 250 * self.GB, 6 * self.GB, 97.7)
        r = DiskUsageTool().execute()
        assert "C:\\ is running low" in r.explanation
        assert "storage.storage_sense" in r.explanation


def test_all_twelve_are_registered(registry):
    names = {t.name for t in registry.all()}
    new = [c.name for c in ALL_DISPLAY_TOOLS + ALL_NETWORK_TOOLS + ALL_STORAGE_TOOLS]
    assert len(new) == 12
    assert set(new) <= names


def test_brightness_command_uses_the_types_wmi_requires():
    # Regression: a plain integer fails on real hardware with "Type mismatch",
    # and calling the method on the class instead of the instance fails too.
    cmd = display.brightness_command(40)
    assert "[byte]40" in cmd and "[uint32]0" in cmd
    assert cmd.startswith("Get-CimInstance") and "| Invoke-CimMethod" in cmd
