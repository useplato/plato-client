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
login_prompt = """
Log in to Mattermost at mattermost:8065 using the credentials username: alex.reynolds, password: password.
"""
url = "http://slack.com"

# Category 1: Posts
post_tasks = [
    PlatoTask(
        name="reply_to_welcome_message",
        prompt=login_prompt + "Find the message about welcoming Jordan in the Town Square channel and reply with 'Welcome to the team, Jordan! Let me know if you need any help getting started.'",
        start_url=url,
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should log in with correct credentials, find the message about welcoming Jordan in Town Square, and reply with the exact text 'Welcome to the team, Jordan! Let me know if you need any help getting started.'"),
        )
    ),
    PlatoTask(
        name="reply_to_project_atlas_message",
        prompt=login_prompt + "Find Chris's message about Project Atlas in Town Square. Reply with 'The Project Atlas launch was a great success! Thanks to everyone who contributed.'",
        start_url=url,
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should find Chris's message about Project Atlas and reply with the exact text 'The Project Atlas launch was a great success! Thanks to everyone who contributed.'"),
        )
    ),
    PlatoTask(
        name="reply_with_formatted_text",
        prompt=login_prompt + "Get the most recent message in the Development channel and reply with a message that includes both bold text and a code block.",
        start_url=url,
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should get the most recent message in the Development channel and reply with a message that contains both bold text (using **text** format) and a code block (using ```code``` format)."),
        )
    ),
    PlatoTask(
        name="reply_with_emoji",
        prompt=login_prompt + "Get the most recent message in the Marketing channel and reply with a message that includes the 🚀 emoji.",
        start_url=url,
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should get the most recent message in the Marketing channel and reply with a message that includes the 🚀 emoji."),
        )
    ),
    PlatoTask(
        name="reply_with_bulleted_list",
        prompt=login_prompt + "Get the most recent message in the Sales channel and reply with a bulleted list of 3 sales priorities.",
        start_url=url,
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should get the most recent message in the Sales channel and reply with a bulleted list (using - or * format) containing exactly 3 sales priorities."),
        )
    ),
    PlatoTask(
        name="reply_with_mention",
        prompt=login_prompt + "Get the most recent message in the Development channel and reply with a message that mentions @ashleigh_lang31.",
        start_url=url,
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should get the most recent message in the Development channel and reply with a message that includes a mention of @ashleigh_lang31."),
        )
    ),
    PlatoTask(
        name="save_message",
        prompt=login_prompt + "Get the most recent message in the Sales channel and save it.",
        start_url=url,
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should get the most recent message in the Sales channel and save it."),
        )
    ),
    PlatoTask(
        name="pin_message",
        prompt=login_prompt + "Get the most recent message in the Sales channel and pin it.",
        start_url=url,
        env_id="mattermost",
        eval_config=CustomEvalConfig( 
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should get the most recent message in the Sales channel and pin it."),
        )
    ),
    PlatoTask(
        name="pin_and_unpin_message",
        prompt=login_prompt + "Get the most recent message in the Sales channel and save it.",
        start_url=url,
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should get the most recent message in the Sales channel and save it."),
        )
    ),
    PlatoTask(
        name="edit_message_content",
        prompt=login_prompt + "Get your most recent message in the General channel and edit it to say 'Final message: team meeting at 3pm tomorrow'.",
        start_url=url,
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should get their most recent message in the General channel and edit it to say 'Final message: team meeting at 3pm tomorrow'."),
        )
    ),
    PlatoTask(
        name="delete_message",
        prompt=login_prompt + "Get your most recent message in the Marketing channel and delete it.",
        start_url=url,
        env_id="mattermost",
        eval_config=CustomEvalConfig( 
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should get the most recent message in the Marketing channel and delete it."),
        )
    ),
    PlatoTask(
        name="edit_to_add_mention",
        prompt=login_prompt + "Get your most recent message in the Marketing channel and edit it to include a mention of @ashleigh_lang31.",
        start_url=url,
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should get their most recent message in the Marketing channel and edit it to include a mention of @ashleigh_lang31."),
        )
    ),
    PlatoTask(
        name="edit_to_add_formatting",
        prompt=login_prompt + "Get your most recent message in the Sales channel and edit it to add bold formatting to at least one word.",
        start_url=url,
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should get their most recent message in the Sales channel and edit it to add bold formatting (using **text**) to at least one word."),
        )
    ),
]

# Category 2: Channels (10 tasks)
channel_tasks = [
    PlatoTask(
        name="create_new_channel",
        prompt=login_prompt + "Create a new public channel called 'product-updates'",
        start_url=url,
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should create a new public channel named 'product-updates'"),
        )
    ),
    PlatoTask(
        name="create_private_channel",
        prompt=login_prompt + "Create a new private channel called 'leadership-team'",
        start_url=url,
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should create a new private channel named 'leadership-team'"),
        )
    ),
    PlatoTask(
        name="create_channel_and_post",
        prompt=login_prompt + "Create a new public channel called 'events' and post a the message 'Welcome to the events channel!'",
        start_url=url,
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should create a new public channel named 'events' and post a the message 'Welcome to the events channel!'"),
        )
    ),
    PlatoTask(
        name="create_channel_with_purpose",
        prompt=login_prompt + "Create a new public channel called 'product-updates' with the purpose 'Sharing product updates and release notes'.",
        start_url=url,
        env_id="mattermost",
        
    ),
    PlatoTask(
        name="create_channel_with_header",
        prompt=login_prompt + "Create a new public channel called 'CI/CD' with a header that includes the message 'This channel is for discussing CI/CD topics.'",
        start_url=url,
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should create a new public channel named 'CI/CD' with a header that includes the message 'This channel is for discussing CI/CD topics.'"),
        )
    ),
    PlatoTask(
        name="delete_channel",
        prompt=login_prompt + "Delete the 'Development' channel.",
        start_url=url,
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should delete the 'Development' channel."),
        )
    ),
    PlatoTask(
        name="rename_channel",
        prompt=login_prompt + "Rename the 'Development' channel to 'Engineering'.",
        start_url=url,
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should rename the 'Development' channel to 'Engineering'."),
        )
    ),
    PlatoTask(
        name="edit_channel_purpose",
        prompt=login_prompt + "Edit the purpose of the 'Sales' channel to 'Discussion of sales pipelines and client opportunities'.",
        start_url=url,
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should edit the purpose of the 'Sales' channel to 'Discussion of sales pipelines and client opportunities'."),
        )
    ),
    PlatoTask(
        name="edit_channel_header",
        prompt=login_prompt + "Edit the header of the 'Marketing' channel to 'Discussion of marketing strategies and campaigns'.",
        start_url=url,
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should edit the header of the 'Marketing' channel to 'Discussion of marketing strategies and campaigns'."),
        )
    ),
    PlatoTask(
        name="create_channel_add_member",
        prompt=login_prompt + "Create a new public channel called 'product-updates' and add @ashleigh_lang31 to it.",
        start_url=url,
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should create a new public channel named 'product-updates' and add @ashleigh_lang31 to it."),
        )
    )
]


# Category 3: Teams
team_tasks = [
    PlatoTask(
        name="join_new_team",
        prompt=login_prompt + "Navigate to the team selection menu, join the 'Nebula Tech', and post a message in its Town Square channel.",
        start_url=url,
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should navigate to the team selection menu, join the 'Nebula Tech', and post any message in the Town Square channel of that team."),
        )
    ),
    PlatoTask(
        name="create_team",
        prompt=login_prompt + "Create a new team called 'Project X' and post a message in its Town Square channel.",
        start_url=url,
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should create a new team named 'Project X' and post any message in the Town Square channel of that team."),
        )
    )
]



# Category 5: Status and availability (5 tasks)
status_tasks = [
   
    PlatoTask(
        name="set_status_message",
        prompt=login_prompt + "Set your status message to 'Working on project documentation'.",
        start_url=url,
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should set their status message to 'Working on project documentation'."),
        )
    ),
    PlatoTask(
        name="change_availability",
        prompt=login_prompt + "Change your availability status from 'Online' to 'Away', then back to 'Online'.",
        start_url=url,
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should change their availability status from 'Online' to 'Away', and then change it back to 'Online'."),
        )
    )
]


# Collect all the tasks
mattermost_tasks = [
    # Website setup task (login)
    PlatoTask(
        name="login_to_mattermost",
        prompt=login_prompt,
        start_url=url,
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should access Mattermost at mattermost:8065 and successfully log in using username 'alex.reynolds' and password 'password'."),
        )
    ),
    
    # Add all category tasks
    *channel_tasks,
    *post_tasks,
    *status_tasks,
    *team_tasks
]

# Collect all the tasks for export
all_tasks = mattermost_tasks
