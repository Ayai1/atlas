from dataclasses import dataclass, field
from typing import Any
@dataclass
class ToolResult:
    """
    return type for tools
    """
    success: bool
    title: str
    data: Any
    explanation: str

    warnings: list[str]=field(default_factory=list)
    