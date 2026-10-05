"""What this computer is, explained without jargon.

Keeps the original hardware detection — real CPU name from the registry, GPU
names from PowerShell — and adds the plain-language reading of those numbers.

The explanation is assembled by us from the real values (principle P7). No
model writes any of this text, which is why it can be trusted.
"""

from __future__ import annotations

import math
import os
import platform
import subprocess
from typing import Any

from engine.tool import Safety, Tool
from engine.tool_result import ToolResult

try:
    import psutil
except ImportError:                    # must still run without it
    psutil = None                      # type: ignore[assignment]

if platform.system() == "Windows":     # pragma: no cover
    import winreg
else:
    winreg = None                      # type: ignore[assignment]


class SystemInfoTool(Tool):
    name = "system.info"
    category = "system"
    description = "Show what hardware and operating system this computer has"
    safety = Safety.READ_ONLY
    parameters: list = []
    keywords = [
        "specs", "specifications", "hardware", "ram", "memory", "cpu",
        "processor", "gpu", "graphics", "disk", "storage", "how much memory",
        "what computer", "system information", "my pc", "slow",
    ]

    # ---- hardware detection ----------------------------------------
    def _get_gpu(self) -> list[str]:
        """GPU names via PowerShell. Returns [] rather than raising."""
        if platform.system() != "Windows":
            return []
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-CimInstance Win32_VideoController | "
                 "Select-Object -ExpandProperty Name"],
                capture_output=True, text=True, timeout=15,
            )
        except (OSError, subprocess.SubprocessError):
            return []
        cleaned = []
        for gpu in result.stdout.strip().splitlines():
            gpu = gpu.replace("(R)", "").replace("(TM)", "")
            gpu = " ".join(gpu.split())
            if gpu:
                cleaned.append(gpu)
        return cleaned

    def _get_cpu(self) -> str:
        """The real processor name, which platform.processor() does not give."""
        if winreg is None:
            return platform.processor() or "unknown"
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            ) as key:
                cpu_name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
        except OSError:
            return platform.processor() or "unknown"
        cpu_name = cpu_name.replace("(R)", "").replace("(TM)", "")
        return " ".join(cpu_name.split())

    def _get_storage(self) -> tuple[int, int]:
        """(total GB, free GB) on the system drive."""
        if psutil is not None:
            disk = psutil.disk_usage(os.path.abspath(os.sep))
        else:
            import shutil
            disk = shutil.disk_usage(os.path.abspath(os.sep))
        return round(disk.total / 1024 ** 3), round(disk.free / 1024 ** 3)

    def _get_ram(self) -> tuple[int, float]:
        """(total GB rounded up, free GB)."""
        if psutil is None:
            return 0, 0.0
        memory = psutil.virtual_memory()
        return (math.ceil(memory.total / 1024 ** 3),
                round(memory.available / 1024 ** 3, 1))

    def _get_cores(self) -> str:
        if psutil is None:
            return "unknown"
        physical = psutil.cpu_count(logical=False)
        logical = psutil.cpu_count(logical=True)
        return (f"{physical} physical, {logical} logical"
                if physical else f"{logical} logical")

    # ---- explaining -------------------------------------------------
    def _explain(self, ram_gb: int, ram_free: float, cores: str,
                 disk_free: int) -> str:
        parts: list[str] = []

        if "physical" in cores:
            n = int(cores.split()[0])
            if n >= 8:
                parts.append(
                    f"You have {n} processor cores, which is plenty for everyday "
                    "work, browsing, and light video or photo editing.")
            elif n >= 4:
                parts.append(
                    f"You have {n} processor cores. That is comfortable for "
                    "everyday work, though heavy editing or many browser tabs "
                    "at once will feel slow.")
            else:
                parts.append(
                    f"You have {n} processor cores, which is on the low side. "
                    "Doing several demanding things at once is where you will "
                    "notice it most.")

        if ram_gb:
            if ram_gb >= 16:
                parts.append(
                    f"{ram_gb} GB of memory is comfortable; you are unlikely to "
                    "run out during normal use.")
            elif ram_gb >= 8:
                parts.append(
                    f"{ram_gb} GB of memory is enough for most things, but it is "
                    "the part of this machine most likely to slow you down when "
                    "a lot is open at once.")
            else:
                parts.append(
                    f"{ram_gb} GB of memory is tight for a modern system. If your "
                    "computer feels slow with several programs open, this is "
                    "almost certainly the reason rather than anything you did.")
            if ram_free and ram_free < 1.5:
                parts.append(
                    f"Right now only {ram_free} GB is free, so closing a few "
                    "programs would probably make things feel faster immediately.")

        os_name = platform.system() if platform.system() != "Darwin" else "macOS"
        if disk_free < 10:
            parts.append(
                f"Only {disk_free} GB of disk space is left. {os_name} needs free "
                "space to work properly, and this little can cause slowdowns and "
                "failed updates.")
        elif disk_free < 25:
            parts.append(
                f"{disk_free} GB of disk space is left, which is getting low. "
                "Worth clearing some out soon.")

        parts.append(
            "Nothing was changed on your computer by this — it only read "
            "information and reported it back.")
        return " ".join(parts)

    # ---- contract ---------------------------------------------------
    def execute(self, **kwargs: Any) -> ToolResult:
        self.validate(**kwargs)

        cores = self._get_cores()
        ram_gb, ram_free = self._get_ram()
        total_gb, free_gb = self._get_storage()
        gpus = self._get_gpu()

        data: dict[str, Any] = {
            "Operating System": f"{platform.system()} {platform.release()}",
            "Architecture": platform.machine(),
            "Processor": self._get_cpu(),
            "Processor cores": cores,
            "Memory": f"{ram_gb} GB total, {ram_free} GB free",
            "Graphics": gpus or ["not detected"],
            "Storage": f"{total_gb} GB total, {free_gb} GB free",
            "Python": platform.python_version(),
        }

        return ToolResult(
            success=True,
            title="This Computer",
            data=data,
            explanation=self._explain(ram_gb, ram_free, cores, free_gb),
            reversible=False,
        )
