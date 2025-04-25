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

# Category 1: Reply to messages (10 tasks)
reply_tasks = [
    PlatoTask(
        name="reply_to_welcome_message",
        prompt="Log in to Mattermost at localhost:8080 using the credentials username: alex.reynolds, password: password. Find Selena's message about welcoming Jordan in the Town Square channel and reply with 'Welcome to the team, Jordan! Let me know if you need any help getting started.'",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should log in with correct credentials, find Selena's message about Jordan in Town Square, and reply with the exact text 'Welcome to the team, Jordan! Let me know if you need any help getting started.'"),
        )
    ),
    PlatoTask(
        name="reply_to_project_atlas_message",
        prompt="Log in to Mattermost and find Eldora's message about Project Atlas in Town Square. Reply with 'The Project Atlas launch was a great success! Thanks to everyone who contributed.'",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should find Eldora's message about Project Atlas and reply with the exact text 'The Project Atlas launch was a great success! Thanks to everyone who contributed.'"),
        )
    ),
    PlatoTask(
        name="reply_to_implementation_post",
        prompt="Navigate to the General channel, find the post about implementation plans, and reply with 'I'll review the CRM implementation plan by tomorrow.'",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should navigate to the General channel, find a post about implementation plans, and reply with the exact text 'I'll review the CRM implementation plan by tomorrow.'"),
        )
    ),
    PlatoTask(
        name="reply_with_formatted_text",
        prompt="Find any message in the Development channel and reply with a message that includes both bold text and a code block.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should find a message in the Development channel and reply with a message that contains both bold text (using **text** format) and a code block (using ```code``` format)."),
        )
    ),
    PlatoTask(
        name="reply_with_emoji",
        prompt="Find any message in the Marketing channel and reply with a message that includes the 🚀 emoji.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should find a message in the Marketing channel and reply with a message that includes the 🚀 emoji."),
        )
    ),
    PlatoTask(
        name="reply_with_bulleted_list",
        prompt="Find any message in the Sales channel and reply with a bulleted list of 3 sales priorities.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should find a message in the Sales channel and reply with a bulleted list (using - or * format) containing exactly 3 sales priorities."),
        )
    ),
    PlatoTask(
        name="reply_with_link",
        prompt="Find any message in the Town Square channel and reply with a message that includes a hyperlink to example.com with the text 'Check this resource'.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should find a message in Town Square and reply with a message that includes a hyperlink to example.com with the display text 'Check this resource'."),
        )
    ),
    PlatoTask(
        name="reply_with_mention",
        prompt="Find any message in the Human Resources channel and reply with a message that mentions @selena_moscicki.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should find a message in the Human Resources channel and reply with a message that includes a mention of @selena_moscicki."),
        )
    ),
    PlatoTask(
        name="reply_with_numbered_list",
        prompt="Find any message in the IT Support channel and reply with a numbered list of 3 IT troubleshooting steps.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should find a message in the IT Support channel and reply with a numbered list (using 1., 2., 3. format) containing exactly 3 IT troubleshooting steps."),
        )
    ),
    PlatoTask(
        name="reply_with_quote",
        prompt="Find any message in the Projects channel and reply by quoting part of the original message and adding your comment.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should find a message in the Projects channel, reply by quoting part of the original message (using > format), and add their own comment after the quote."),
        )
    ),
]

# Category 2: Create channels or teams (10 tasks)
create_tasks = [
    PlatoTask(
        name="create_new_channel",
        prompt="Create a new public channel called 'product-updates' with the purpose 'Sharing product updates and release notes'.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should create a new public channel named 'product-updates' with the purpose 'Sharing product updates and release notes'."),
        )
    ),
    PlatoTask(
        name="create_private_channel",
        prompt="Create a new private channel called 'leadership-team' with the purpose 'Confidential discussions for leadership'.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should create a new private channel named 'leadership-team' with the purpose 'Confidential discussions for leadership'."),
        )
    ),
    PlatoTask(
        name="create_channel_and_post",
        prompt="Create a new public channel called 'events' with the purpose 'Upcoming company events and gatherings', then post a welcome message in the channel.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should create a new public channel named 'events' with the purpose 'Upcoming company events and gatherings', then post any welcome message in the new channel."),
        )
    ),
    PlatoTask(
        name="create_channel_with_header",
        prompt="Create a new public channel called 'engineering' with a purpose and a header that includes a link to a documentation site.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should create a new public channel named 'engineering' with any purpose and a header that includes a hyperlink to any documentation site."),
        )
    ),
    PlatoTask(
        name="join_new_team",
        prompt="Navigate to the team selection menu, join the 'Test Team', and post a message in its Town Square channel.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should navigate to the team selection menu, join the 'Test Team', and post any message in the Town Square channel of that team."),
        )
    ),
    PlatoTask(
        name="create_team",
        prompt="Create a new team called 'Project X' with the URL 'project-x' and post a message in its Town Square channel.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should create a new team named 'Project X' with the URL 'project-x' and post any message in the Town Square channel of that team."),
        )
    ),
    PlatoTask(
        name="create_channel_with_emoji",
        prompt="Create a new channel with an emoji in its name - '📱mobile-app' and set an appropriate purpose.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should create a new channel with the emoji '📱' in its name, specifically '📱mobile-app' (or similar format), and set any appropriate purpose."),
        )
    ),
    PlatoTask(
        name="browse_public_channels",
        prompt="Browse the list of available public channels, join the 'Announcements' channel, and post a test message.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should browse the list of public channels, join the 'Announcements' channel, and post any test message in it."),
        )
    ),
    PlatoTask(
        name="create_and_switch_channels",
        prompt="Create two new channels: 'project-alpha' and 'project-beta'. Post a unique message in each channel, then switch between them.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should create two new channels named 'project-alpha' and 'project-beta', post a different message in each channel, and switch between the two channels."),
        )
    ),
    PlatoTask(
        name="leave_and_rejoin_channel",
        prompt="Join the Training channel if not already a member, then leave the channel, and finally rejoin it.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should join the Training channel if not already a member, then leave the channel, and finally rejoin the same channel."),
        )
    ),
]

# Category 3: Manage user permissions (10 tasks)
permissions_tasks = [
    PlatoTask(
        name="view_channel_members",
        prompt="Open the Development channel, view the list of channel members, and identify at least one member besides yourself.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should open the Development channel, access the member list, and identify at least one other member in the channel."),
        )
    ),
    PlatoTask(
        name="make_channel_favorite",
        prompt="Add the Marketing channel to your favorites list, then verify it appears in your favorites section.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should add the Marketing channel to their favorites list and verify it appears in the favorites section of the sidebar."),
        )
    ),
    PlatoTask(
        name="mute_channel",
        prompt="Mute the IT Support channel, then verify it shows as muted in your channel list.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should mute the IT Support channel and verify it shows as muted in the channel list in the sidebar."),
        )
    ),
    PlatoTask(
        name="invite_user_to_channel",
        prompt="Create a new channel called 'special-project' and invite selena_moscicki to join it.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should create a new channel named 'special-project' and invite the user selena_moscicki to join this channel."),
        )
    ),
    PlatoTask(
        name="view_team_members",
        prompt="View the full list of members in the Enterprise Solutions team and identify at least three members.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should view the full list of members in the Enterprise Solutions team and be able to identify at least three distinct team members."),
        )
    ),
    PlatoTask(
        name="access_channel_settings",
        prompt="Access the channel settings for Sales channel, view the existing purpose, and add a new header with the text 'Discussion of sales pipelines and client opportunities'.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should access the channel settings for the Sales channel, view its current purpose, and add a new header with the text 'Discussion of sales pipelines and client opportunities'."),
        )
    ),
    PlatoTask(
        name="rename_channel",
        prompt="Create a new channel called 'temp-channel', then rename it to 'renamed-channel'.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should create a new channel named 'temp-channel', then rename that same channel to 'renamed-channel'."),
        )
    ),
    PlatoTask(
        name="archive_channel",
        prompt="Create a new channel called 'archive-test', then archive this channel.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should create a new channel named 'archive-test', then archive this channel using the channel settings."),
        )
    ),
    PlatoTask(
        name="set_channel_description",
        prompt="Navigate to the Human Resources channel and update its purpose to include 'Employee benefits and workplace policies discussions'.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should navigate to the Human Resources channel and update its purpose to include the text 'Employee benefits and workplace policies discussions'."),
        )
    ),
    PlatoTask(
        name="check_notification_settings",
        prompt="Access your account settings, navigate to notifications, and review your current notification settings for desktop notifications.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should access their account settings, navigate to notification settings, and review their current desktop notification settings."),
        )
    ),
]

# Category 4: Edit and delete messages (10 tasks)
edit_delete_tasks = [
    PlatoTask(
        name="edit_message_content",
        prompt="Post a message in the General channel saying 'Draft message', then edit it to say 'Final message: team meeting at 3pm tomorrow'.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should post a message in the General channel with the text 'Draft message', then edit that same message to read 'Final message: team meeting at 3pm tomorrow'."),
        )
    ),
    PlatoTask(
        name="delete_message",
        prompt="Post a message in the Projects channel with the text 'This message will be deleted', then delete that message.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should post a message in the Projects channel with the text 'This message will be deleted', then delete that same message."),
        )
    ),
    PlatoTask(
        name="add_reaction_to_message",
        prompt="Find any message in the Town Square channel and add a thumbs up reaction to it.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should find any message in the Town Square channel and add a thumbs up reaction to it."),
        )
    ),
    PlatoTask(
        name="remove_reaction",
        prompt="Find any message with a reaction in the Development channel, then remove that reaction (or add a reaction and then remove it if none exist).",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should find a message with a reaction in the Development channel and remove that reaction, or if no reactions exist, add one and then remove it."),
        )
    ),
    PlatoTask(
        name="edit_to_add_mention",
        prompt="Post a message in the Marketing channel, then edit it to include a mention of @selena_moscicki.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should post any message in the Marketing channel, then edit that message to include a mention of @selena_moscicki."),
        )
    ),
    PlatoTask(
        name="edit_to_add_formatting",
        prompt="Post a plain text message in the Sales channel, then edit it to add bold formatting to at least one word.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should post a plain text message in the Sales channel, then edit that message to add bold formatting (using **text**) to at least one word."),
        )
    ),
    PlatoTask(
        name="pin_message",
        prompt="Post a message in the Announcements channel with the text 'Important update', then pin that message.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should post a message in the Announcements channel with the text 'Important update', then pin that message."),
        )
    ),
    PlatoTask(
        name="unpin_message",
        prompt="Find a pinned message in any channel (or pin a message first), then unpin that message.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should find a pinned message in any channel (or pin a message first if none exist), then unpin that message."),
        )
    ),
    PlatoTask(
        name="flag_message",
        prompt="Find any message in the IT Support channel and flag it for follow-up.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should find any message in the IT Support channel and flag it for follow-up."),
        )
    ),
    PlatoTask(
        name="unflag_message",
        prompt="View your flagged posts, then unflag at least one message.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should view their flagged posts and unflag at least one message that was previously flagged (may need to flag a message first if none exist)."),
        )
    ),
]

# Category 5: General navigation and user settings (10 tasks)
navigation_tasks = [
    PlatoTask(
        name="search_messages",
        prompt="Use the search function to find messages containing the word 'implementation', then click on one of the search results.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should use the search function to find messages containing 'implementation', then click on one of the search results to view it in context."),
        )
    ),
    PlatoTask(
        name="view_recent_mentions",
        prompt="Access your recent mentions through the @ symbol at the top of the screen and view any messages where you were mentioned.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should access their recent mentions through the @ symbol at the top of the screen and view any messages where they were mentioned."),
        )
    ),
    PlatoTask(
        name="switch_between_teams",
        prompt="Switch from the Enterprise Solutions team to the Nebula Tech team, then back to Enterprise Solutions.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should switch from the Enterprise Solutions team to the Nebula Tech team, and then switch back to the Enterprise Solutions team."),
        )
    ),
    PlatoTask(
        name="change_profile_picture",
        prompt="Access your account settings and change your profile picture (or view the current picture settings).",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should access their account settings and either change their profile picture or view the current profile picture settings."),
        )
    ),
    PlatoTask(
        name="update_display_name",
        prompt="Access your account settings and update your display name to include both first and last name.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should access their account settings and update their display name to include both a first and last name."),
        )
    ),
    PlatoTask(
        name="set_status_message",
        prompt="Set your status message to 'Working on project documentation' with the 📝 emoji.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should set their status message to 'Working on project documentation' with the 📝 emoji."),
        )
    ),
    PlatoTask(
        name="change_availability",
        prompt="Change your availability status from 'Online' to 'Away', then back to 'Online'.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should change their availability status from 'Online' to 'Away', and then change it back to 'Online'."),
        )
    ),
    PlatoTask(
        name="view_saved_posts",
        prompt="Flag any message in Town Square, then access your saved posts to view it.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should flag any message in Town Square, then access their saved posts and verify the flagged message appears there."),
        )
    ),
    PlatoTask(
        name="view_channel_info",
        prompt="Open the Projects channel and view its information, including purpose and member count.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should open the Projects channel and view its information, including the channel purpose and member count."),
        )
    ),
    PlatoTask(
        name="use_keyboard_shortcuts",
        prompt="Press Ctrl+/ or Cmd+/ to view the list of keyboard shortcuts, then use at least one shortcut (e.g., Alt+Up to navigate to previous channel).",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should press Ctrl+/ or Cmd+/ to view keyboard shortcuts, then use at least one keyboard shortcut to perform an action."),
        )
    ),
]

# Collect all the tasks
mattermost_tasks = [
    # Website setup task (login)
    PlatoTask(
        name="login_to_mattermost",
        prompt="Access Mattermost at localhost:8080 and log in with username: alex.reynolds, password: password.",
        start_url="http://localhost:8080",
        env_id="mattermost",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The user should access Mattermost at localhost:8080 and successfully log in using username 'alex.reynolds' and password 'password'."),
        )
    ),
    
    # Add all category tasks
    *reply_tasks,
    *create_tasks,
    *permissions_tasks,
    *edit_delete_tasks,
    *navigation_tasks
]

# Collect all the tasks for export
all_tasks = mattermost_tasks