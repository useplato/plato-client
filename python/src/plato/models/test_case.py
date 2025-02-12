from typing import Any, Optional

from pydantic import BaseModel


class TestCase(BaseModel):
    name: str
    prompt: str
    start_url: Optional[str] = None
    output_schema: Optional[Any] = None
    extra: dict = {}

    def to_dict(self) -> dict:
        """Convert the test case to a dictionary suitable for JSON serialization."""
        data = {
            "name": self.name,
            "prompt": self.prompt,
        }
        if self.start_url:
            data["startUrl"] = self.start_url
        if self.output_schema:
            data["outputSchema"] = (
                self.output_schema.schema()
                if hasattr(self.output_schema, "schema")
                else self.output_schema
            )
        data.update(self.extra)
        return data
