import os
import math
import platform
import psutil
import winreg
import subprocess
from engine.tool import Tool
from engine.tool_result import ToolResult



class SystemInfoTool(Tool):
    name = "Atlas System Information"
    description = "Retrieve basic information about the current computer."
    category = "System"

    def _get_gpu(self) ->list[str]:
        result = subprocess.run(
            [
            "powershell",
            "-Command",
            "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"
            ],
            capture_output=True,
            text=True,
        )

        gpus = result.stdout.strip().splitlines()
        cleaned=[]
        for gpu in gpus:
            gpu = gpu.replace("(R)", "")
            gpu = gpu.replace("(TM)", "")
            gpu = " ".join(gpu.split())
            cleaned.append(gpu)
        return cleaned
    
    def _get_cpu(self) -> str:
        """
        Return the CPU name.
        """

        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
        )

        cpu_name, _ = winreg.QueryValueEx(
            key,
            "ProcessorNameString"
        )
        cpu_name = cpu_name.replace("(R)", "")
        cpu_name = cpu_name.replace("(TM)", "")
        cpu_name = " ".join(cpu_name.split())
        return cpu_name 
    
    def _get_storage(self) -> str:
        """
        Return the total storage capacity of the system drive.
        """
        disk = psutil.disk_usage(os.path.abspath(os.sep))
        total_gb = round(disk.total / (1024 ** 3))
        return f"{total_gb} GB"
    
    def _get_ram(self) -> int:
        """
        Return the total system memory in GB.
         """
        memory = psutil.virtual_memory()
        return math.ceil(memory.total / (1024 ** 3))
    
    def _get_operating_system(self) -> str:
        return f"{platform.system()} {platform.release()}"


    def _get_architecture(self) -> str:
        return platform.machine()


    def _get_python_version(self) -> str:
        return platform.python_version()
    
    def execute(self) -> ToolResult:
        operating_system = self._get_operating_system()
        architecture = self._get_architecture()
        processor = self._get_cpu()
        python_version = self._get_python_version()
        gpus = self._get_gpu()
        ram = self._get_ram()
        storage = self._get_storage()

        return ToolResult(
            success=True,
            title=self.name,
            data={
                "Operating System": operating_system,
                "Architecture": architecture,
               "Processor" : processor,
                "Python" : python_version,
                "RAM":f"{ram} GB",
                "GPU": gpus,
                "Storage": storage,
            },
            explanation="Successfully retrieved system information.",
        )