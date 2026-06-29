from abc import ABC, abstractmethod
from engine.tool_result import ToolResult

class Tool(ABC):
    """
    Base class for every Atlas tool.

    Every tool must be able to:
    - execute an action
    - explain what it did
    """
    name: str
    description: str
    category: str

    @abstractmethod
    def execute(self) -> ToolResult:
        """
        Execute the tool.
        """
        pass