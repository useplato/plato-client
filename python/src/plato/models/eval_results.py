from typing import Any, List

from pydantic import BaseModel


class EvalSummary(BaseModel):
    total: int
    success: int
    failure: int
    score: float

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "success": self.success,
            "failure": self.failure,
            "score": self.score,
        }


class EvalResult(BaseModel):
    summary: EvalSummary
    results: List[Any]

    def to_dict(self) -> dict:
        return {
            "summary": self.summary.to_dict(),
            "results": self.results,
        }
