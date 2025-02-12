from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class TestCase(BaseModel):
    id: int
    name: str
    prompt: str
    start_url: Optional[str] = Field(default=None, alias="startUrl")
    config: Dict[str, Any]
