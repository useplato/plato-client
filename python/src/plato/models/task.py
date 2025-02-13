from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class Task(BaseModel):
    """
    Represents a single task to be evaluated.
    """

    id: int

    name: str
    prompt: str
    start_url: str = Field(alias="startUrl")

    test_case_set_id: Optional[int] = Field(None, alias="testCaseSetId")
    config: Dict[str, Any] = {}
