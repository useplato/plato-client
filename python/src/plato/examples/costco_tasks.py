import json
from typing import Tuple
from plato.models.task import CustomEvalConfig, PlatoTask
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
      {"role": "user", "content": f"prompt: {prompt}\n orders: {json.dumps(data['state']['consumer_orders'])}"},
    ],
    response_format=LLMJudgeResponseFormat
  )
  return response.choices[0].message.parsed.success, response.choices[0].message.parsed.reason

costco_specific_easy_tasks = [
    PlatoTask(
        name="order_kirkland_water",
        prompt="order a 40-pack of Kirkland Signature Purified Water",
        start_url="https://www.costco.com",
        env_id="costco", # This env_id will need to be created in Plato
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with a 40-pack of Kirkland Signature Purified Water."),
        )
    ),
    PlatoTask(
        name="order_rotisserie_chicken",
        prompt="order a Kirkland Signature Rotisserie Chicken",
        start_url="https://www.costco.com",
        env_id="costco",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with a Kirkland Signature Rotisserie Chicken."),
        )
    ),
]

all_tasks = costco_specific_easy_tasks 