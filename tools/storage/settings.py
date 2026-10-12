"""Storage: how full the disks are, and Storage Sense.

Storage Sense is Windows' own cleaner. Its options are per-user registry
values, so none of these needs administrator rights.

One option is deliberately missing: "delete files in my Downloads folder".
Changing that setting is reversible, but the files it then deletes are not,
and Atlas does not make changes it cannot undo. The Recycle Bin option is
included because those files were already deleted once by their owner; it
still carries a warning.
"""

from __future__ import annotations

from typing import Any

import psutil

from engine.tool import Safety, Tool, ToolResult
from tools.registry_choice import RegistryChoiceTool
from windows import winsettings as ws

_WHERE = "Settings, then System, then Storage, then Storage Sense"


def _gb(n: int) -> float:
    return round(n / 1024 ** 3, 1)


class DiskUsageTool(Tool):
    name = "storage.disk_usage"
    category = "storage"
    description = "How full each drive is, and whether that is a problem"
    safety = Safety.READ_ONLY
    keywords = [
        "disk", "drive", "space", "full", "storage", "free space", "c drive",
        "running out", "low disk", "gb", "room", "cant install", "update fails",
    ]

    def execute(self, **kwargs: Any) -> ToolResult:
        self.validate(**kwargs)
        data: dict[str, Any] = {}
        tight: list[str] = []
        for part in psutil.disk_partitions(all=False):
            if "cdrom" in part.opts or not part.fstype:
                continue
            try:
                u = psutil.disk_usage(part.mountpoint)
            except (PermissionError, OSError):
                continue
            free_pct = 100 - u.percent
            data[part.mountpoint] = (f"{_gb(u.free)} GB free of {_gb(u.total)} GB "
                                     f"({free_pct:.0f}% free)")
            if free_pct < 10 or u.free < 10 * 1024 ** 3:
                tight.append(part.mountpoint)

        if not data:
            explanation = "No drives could be read."
        elif tight:
            explanation = (
                f"{', '.join(tight)} is running low. Below about 10% free, or "
                "10 GB, Windows updates can fail and the computer can slow "
                "down. Windows' own cleaner can help: 'atlas set "
                "storage.storage_sense on'. Emptying the Recycle Bin and "
                "uninstalling programs you no longer use free space too."
            )
        else:
            explanation = ("Every drive has comfortable free space. Nothing "
                           "needs doing.")
        return ToolResult(title="Disk Usage", data=data, explanation=explanation)


class StorageSenseTool(RegistryChoiceTool):
    name = "storage.storage_sense"
    category = "storage"
    description = "Whether Windows automatically cleans up temporary files to free space"
    result_title = "Storage Sense"
    setting = ws.STORAGE_SENSE
    labels = {0: ("off", "off"), 1: ("on", "on")}
    choice_hint = "Turn Windows' automatic cleanup on or off."
    where = _WHERE
    keywords = [
        "storage sense", "clean", "cleanup", "clean up", "free space",
        "disk full", "automatic", "automatically", "temporary", "junk",
        "space",
    ]

    def meaning(self, raw: int) -> str:
        if raw == 1:
            return ("Windows will clear temporary files on the schedule set "
                    "by 'storage.storage_sense_schedule'. It never touches "
                    "your documents, pictures or Downloads folder.")
        return "Windows will not clean up automatically."


class StorageSenseScheduleTool(RegistryChoiceTool):
    name = "storage.storage_sense_schedule"
    category = "storage"
    description = "How often Storage Sense runs its cleanup"
    result_title = "Storage Sense schedule"
    setting = ws.STORAGE_SENSE_SCHEDULE
    labels = {
        1: ("every_day", "every day"),
        7: ("every_week", "every week"),
        30: ("every_month", "every month"),
        0: ("low_disk_space", "only when free space runs low"),
    }
    choice_hint = "How often Storage Sense cleans up."
    where = _WHERE
    keywords = ["storage sense", "schedule", "how often", "every day",
                "every week", "cleanup", "run"]

    def meaning(self, raw: int) -> str:
        return "This only matters while Storage Sense is on."


class TempFilesCleanupTool(RegistryChoiceTool):
    name = "storage.temp_files_cleanup"
    category = "storage"
    description = ("Whether Storage Sense deletes temporary files that apps "
                   "left behind")
    result_title = "Temporary files cleanup"
    setting = ws.STORAGE_SENSE_TEMP
    labels = {0: ("off", "off"), 1: ("on", "on")}
    choice_hint = "Whether leftover temporary files are cleaned up."
    where = _WHERE
    keywords = ["temp", "temporary", "junk", "leftover", "cache", "cleanup",
                "clean"]

    def meaning(self, raw: int) -> str:
        if raw == 1:
            return ("Temporary files are ones apps create and no longer use; "
                    "deleting them is safe.")
        return ""


class RecycleBinCleanupTool(RegistryChoiceTool):
    name = "storage.recycle_bin_cleanup"
    category = "storage"
    description = ("How long deleted files stay in the Recycle Bin before "
                   "Storage Sense empties them")
    result_title = "Recycle Bin cleanup"
    setting = ws.STORAGE_SENSE_RECYCLE_DAYS
    labels = {
        0: ("never", "never (files stay until you empty it)"),
        1: ("1_day", "after 1 day"),
        14: ("14_days", "after 14 days"),
        30: ("30_days", "after 30 days"),
        60: ("60_days", "after 60 days"),
    }
    choice_hint = "How long files stay in the Recycle Bin."
    where = _WHERE
    keywords = ["recycle bin", "recycle", "bin", "trash", "deleted files",
                "empty", "emptied", "restore", "disappeared", "gone"]

    def meaning(self, raw: int) -> str:
        if raw == 0:
            return ("Storage Sense will never empty the Recycle Bin, so you "
                    "can always restore something you deleted.")
        return "This only matters while Storage Sense is on."

    def warnings_for(self, raw: int) -> list[str]:
        if raw == 0:
            return []
        return ["once Storage Sense empties a file from the Recycle Bin it is "
                "gone for good. 'atlas undo' restores this setting, not the "
                "files."]


ALL_STORAGE_TOOLS = [
    DiskUsageTool, StorageSenseTool, StorageSenseScheduleTool,
    TempFilesCleanupTool, RecycleBinCleanupTool,
]
