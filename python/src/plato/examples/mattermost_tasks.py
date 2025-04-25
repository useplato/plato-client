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
      {"role": "user", "content": f"prompt: {prompt}\n\ndata: {json.dumps(data)}"},
    ],
    response_format=LLMJudgeResponseFormat
  )

  # Access the parsed response safely
  if hasattr(response.choices[0].message, 'parsed') and response.choices[0].message.parsed is not None:
    return response.choices[0].message.parsed.success, response.choices[0].message.parsed.reason
  else:
    # Fallback if parsed is not available
    content = response.choices[0].message.content
    if content is not None:
      try:
        # Try to parse the content as JSON
        parsed_content = json.loads(content)
        return parsed_content.get('success', False), parsed_content.get('reason', 'Unknown reason')
      except:
        # If parsing fails, make a best effort determination
        success = 'true' in content.lower()
        reason = content
        return success, reason
    else:
      # If content is None, return default values
      return False, "Unable to determine result: response content is None"


# 💬 mattermost tasks
# Test tasks for evaluating Mattermost platform usage

mattermost_tasks = [
    PlatoTask(
        name="login_and_post_town_square",
        prompt="Log in to the Mattermost instance at localhost:80 using the credentials username: alex.reynolds, password: password. Navigate to the Town Square channel and post a message saying 'Checking Project Atlas announcement'.",
        start_url="http://localhost:80",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should log in to Mattermost with username alex.reynolds and password 'password', navigate to Town Square channel, and post a message with the exact text 'Checking Project Atlas announcement'."),
        )
    ),
    PlatoTask(
        name="post_in_general_channel",
        prompt="Navigate to the General channel and post a message saying 'Reviewing General channel content'.",
        start_url="http://localhost:80",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should navigate to the General channel and post a message with the exact text 'Reviewing General channel content'."),
        )
    ),
    PlatoTask(
        name="post_in_development_channel",
        prompt="Switch to the Development channel and post a message containing the text 'Looking for code discussions'.",
        start_url="http://localhost:80",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should navigate to the Development channel and post a message with the exact text 'Looking for code discussions'."),
        )
    ),
    PlatoTask(
        name="search_implementation_term",
        prompt="Perform a search for the term 'implementation' and click on at least one search result.",
        start_url="http://localhost:80",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should perform a search for the term 'implementation' and click on at least one of the search results."),
        )
    ),
    PlatoTask(
        name="post_in_marketing_channel",
        prompt="Navigate to the Marketing channel and post a message saying 'Need update on quarterly marketing plan by Friday'.",
        start_url="http://localhost:80",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should navigate to the Marketing channel and post a message with the exact text 'Need update on quarterly marketing plan by Friday'."),
        )
    ),
    PlatoTask(
        name="reply_to_message_about_jordan",
        prompt="In Town Square, post a reply to selena_moscicki's message about Jordan with text 'Welcome to the team, Jordan!'.",
        start_url="http://localhost:80",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should find selena_moscicki's message about Jordan in Town Square and post a reply with the exact text 'Welcome to the team, Jordan!'."),
        )
    ),
    PlatoTask(
        name="add_reaction_to_message",
        prompt="Add a thumbs up reaction to eldora.walter's message about Project Atlas.",
        start_url="http://localhost:80",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should find eldora.walter's message about Project Atlas and add a thumbs up reaction to it."),
        )
    ),
    PlatoTask(
        name="edit_posted_message",
        prompt="Post a message saying 'Typo here', then edit that message to say 'Edited: No typo here anymore'.",
        start_url="http://localhost:80",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should post a message with the text 'Typo here' and then edit that same message to have the text 'Edited: No typo here anymore'."),
        )
    ),
    PlatoTask(
        name="post_link_in_sales_channel",
        prompt="Post a message in the Sales channel containing the link 'https://example.com' with text 'Check this resource'.",
        start_url="http://localhost:80",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should navigate to the Sales channel and post a message containing the link 'https://example.com' with the text 'Check this resource'."),
        )
    ),
    PlatoTask(
        name="post_formatted_message",
        prompt="Post a message in Town Square that includes bold text and a bulleted list with exactly 3 items.",
        start_url="http://localhost:80",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should post a message in Town Square that contains bold text and a bulleted list with exactly 3 items."),
        )
    ),
    PlatoTask(
        name="mention_user_in_message",
        prompt="Post a message that mentions @selena_moscicki with text '@selena_moscicki please review when you have time'.",
        start_url="http://localhost:80",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should post a message that mentions @selena_moscicki with the exact text '@selena_moscicki please review when you have time'."),
        )
    ),
    PlatoTask(
        name="create_thread_reply",
        prompt="Find eldora.walter's message about Project Atlas and create a new thread reply with text 'Starting new discussion thread'.",
        start_url="http://localhost:80",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should find eldora.walter's message about Project Atlas and create a new thread reply with the exact text 'Starting new discussion thread'."),
        )
    ),
    PlatoTask(
        name="check_notifications",
        prompt="Click on your notification bell icon and view any notifications.",
        start_url="http://localhost:80",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should click on the notification bell icon and view any notifications."),
        )
    ),
    PlatoTask(
        name="change_status",
        prompt="Click on your profile picture in the top-right corner and change your status to 'Do Not Disturb'.",
        start_url="http://localhost:80",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should click on their profile picture in the top-right corner and change their status to 'Do Not Disturb'."),
        )
    ),
    PlatoTask(
        name="complete_login_flow",
        prompt="Log out of Mattermost, then log back in with username: alex.reynolds, password: password.",
        start_url="http://localhost:80",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should log out of Mattermost and then successfully log back in with username alex.reynolds and password 'password'."),
        )
    )
]


# Collect all the tasks
all_tasks = mattermost_tasks
