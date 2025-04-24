import json
from typing import Tuple
from plato.models.task import PlatoTask
from openai import AsyncOpenAI
from pydantic import BaseModel

client = AsyncOpenAI()

class LLMJudgeResponseFormat(BaseModel):
  success: bool
  reason: str

async def llm_judge_eval_fn(data: dict, prompt: str) -> Tuple[bool, str]:
  response = await client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=[
      {"role": "system", "content": "Your job is to judge whether the given prompt is satisfied by the given data. If it is, return 'true'. If it is not, return 'false'. Also include the reason for the score."},
      {"role": "user", "content": f"prompt: {prompt}\n\ndata: {json.dumps(data)}"},
    ],
    response_format=LLMJudgeResponseFormat
  )
  return response.choices[0].message.parsed.success, response.choices[0].message.parsed.reason




# Tasks that should have only one correct answer with zero ambiguity
specific_easy_tasks = [
    PlatoTask(
        name="book_1_bedroom_apartment_in_manhattan",
        prompt="book a 1 bedroom apartment in Manhattan between June 4th - June 7th.",
        start_url="https://www.airbnb.com",
        env_id="airbnb",
        # eval_config=CustomEvalConfig(
        #   type="custom",
        #   score_fn=lambda x: llm_judge_eval_fn(x, "There should be a booking for a 1 bedroom apartment in Manhattan between June 4th - June 7th"),
        # )
    ),
]

all_tasks = specific_easy_tasks
