"""Shortlist retrieval — the layer a local model will sit on top of."""

import pytest


@pytest.mark.parametrize("phrasing,expected", [
    ("my screen keeps going dark while I read", "power.monitor_timeout"),
    ("the display turns off too fast", "power.monitor_timeout"),
    ("stop my monitor from going black", "power.monitor_timeout"),
    ("how do I make my computer sleep later", "power.sleep_timeout"),
    ("the pc keeps going to sleep", "power.sleep_timeout"),
    ("my laptop goes to sleep when I close the lid", "power.lid_close_action"),
    ("keep the laptop running with the lid closed for my external monitor",
     "power.lid_close_action"),
    ("pressing the power button shuts down my pc", "power.power_button_action"),
    ("my computer wakes up by itself in the middle of the night",
     "power.wake_timers"),
    ("my usb mouse keeps disconnecting", "power.usb_selective_suspend"),
    ("my wifi keeps dropping on battery", "power.wifi_power_saving"),
    ("my laptop gets really hot and the fan is loud", "power.max_processor_state"),
    ("battery dies overnight while asleep", "power.hibernate_after"),
    ("warn me earlier when battery is low", "power.low_battery_level"),
    ("laptop shuts off suddenly when battery is empty",
     "power.critical_battery_action"),
    ("switch to high performance power plan", "power.plan"),
    ("my external hard drive keeps spinning down", "power.disk_timeout"),
    ("stop my pc from sleeping", "power.sleep_timeout"),
    ("my laptop battery drains while sleeping", "power.hibernate_after"),
    ("computer turns on by itself", "power.wake_timers"),
    ("my bluetooth mouse disconnects", "power.usb_selective_suspend"),
    ("fan noise", "power.max_processor_state"),
    ("screen turns off when I close the lid", "power.lid_close_action"),
    ("my screen is too bright", "display.brightness"),
    ("make the screen dimmer", "display.brightness"),
    ("brightness keeps changing by itself", "display.adaptive_brightness"),
    ("the taskbar is white", "display.windows_theme"),
    ("the taskbar is see through and hard to read", "display.transparency"),
    ("is my internet working", "network.status"),
    ("am I connected", "network.status"),
    ("websites wont load", "network.proxy"),
    ("my c drive is full", "storage.disk_usage"),
    ("I am running out of disk space", "storage.disk_usage"),
    ("clean up junk files automatically", "storage.storage_sense"),
    ("how long do deleted files stay in the recycle bin",
     "storage.recycle_bin_cleanup"),
    ("my screen keeps going dark", "power.monitor_timeout"),
    ("how much memory do I have", "system.info"),
    ("what are my specs", "system.info"),
    ("show me my hardware", "system.info"),
])
def test_real_phrasings_find_the_right_tool(registry, phrasing, expected):
    matches = registry.shortlist(phrasing)
    assert matches, f"nothing matched {phrasing!r}"
    assert matches[0][0].name == expected, (
        f"{phrasing!r} -> {matches[0][0].name}, expected {expected}"
    )


def test_scores_are_normalised(registry):
    for _tool, score in registry.shortlist("screen goes dark"):
        assert 0 < score <= 1


def test_nonsense_matches_nothing(registry):
    assert registry.shortlist("xyzzy plugh frobnicate") == []


def test_stopwords_alone_match_nothing(registry):
    assert registry.shortlist("the a of my is it") == []


def test_shortlist_respects_limit(registry):
    assert len(registry.shortlist("screen sleep memory timeout", limit=2)) <= 2
