"""
Base tool model and interface for Osaka tools
"""

from typing import Dict, Any
from pydantic import BaseModel


class Tool(BaseModel):
    """Base model for tool definitions"""
    name: str
    description: str
    input_schema: Dict[str, Any]