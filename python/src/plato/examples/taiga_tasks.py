import json
from typing import Tuple
from plato.models.task import EnumMatchVariable, MutationVariable, PlatoTask, SemanticMatchVariable, StateMutationMatch, StateMutationMatchEvalConfig
from openai import AsyncOpenAI
from pydantic import BaseModel

import json
from typing import Dict, List, Tuple

from openai import AsyncOpenAI
from pydantic import BaseModel
from plato.models.task import CustomEvalConfig, PlatoTask
client = AsyncOpenAI()

# Define a constant for the Taiga start URL
TAIGA_URL = "http://taiga.com"  # Placeholder URL for Taiga



class LLMJudgeResponseFormat(BaseModel):
    success: bool
    reason: str


async def llm_judge_eval_fn(data: dict, prompt: str) -> Tuple[bool, str]:
    response = await client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "Your job is to judge whether the given prompt is satisfied by the given data. If it is, return 'true'. If it is not, return 'false'. Also include the reason for the score.",
            },
            {
                "role": "user",
                "content": f"prompt: {prompt}\n\ndata: {json.dumps(data)}",
            },
        ],
        response_format=LLMJudgeResponseFormat,
    )

    # Access the parsed response safely
    if (
        hasattr(response.choices[0].message, "parsed")
        and response.choices[0].message.parsed is not None
    ):
        return response.choices[0].message.parsed.success, response.choices[
            0
        ].message.parsed.reason
    else:
        # Fallback if parsed is not available
        content = response.choices[0].message.content
        if content is not None:
            try:
                # Try to parse the content as JSON
                parsed_content = json.loads(content)
                return parsed_content.get("success", False), parsed_content.get(
                    "reason", "Unknown reason"
                )
            except:
                # If parsing fails, make a best effort determination
                success = "true" in content.lower()
                reason = content
                return success, reason
        else:
            # If content is None, return default values
            return False, "Unable to determine result: response content is None"

# Project setup and user management tasks
project_setup_tasks = [
    PlatoTask(
        name="create_a_new_user",
        prompt="Create a new user",
        env_id="taiga",
        start_url=TAIGA_URL,
    ),

    PlatoTask(
        name="create_scrum_project",
        prompt="Create a new project named 'Website Redesign' using the Scrum template, set to private, and use a custom project slug like web-redesign-2025",
        env_id="taiga",
        start_url=TAIGA_URL,
    ),

    PlatoTask(
        name="setup_kanban_project",
        prompt="Set up a Kanban project (title: 'Website Maintenance'), set it to public, and custom project slug: 'website-maintenance-2025'",
        env_id="taiga",
        start_url=TAIGA_URL,
    ),
]

# Sprint management tasks
sprint_management_tasks = [
    PlatoTask(
        name="create_overlapping_sprints",
        prompt="Create 3 sprints with overlapping dates (invalid) to test UI error handling: Sprint 1: May 20 – June 3, Sprint 2: May 30 – June 10, Sprint 3: June 4 – June 18",
        env_id="taiga",
        start_url=TAIGA_URL,
    ),
]

# User story management tasks
user_story_tasks = [
    PlatoTask(
        name="create_user_story_with_attachments",
        prompt="Create user story (title 'Homepage Redesign') with description: 'Reworking the landing page UI', attach 'wireframe.pdf' and 'homepage_mockup.jpg' files, and add criteria checklist with: 'responsive layout', 'navigation rework', and 'content structure'",
        env_id="taiga",
        start_url=TAIGA_URL,
    ),

    PlatoTask(
        name="create_story_with_subtasks",
        prompt="Create a new story: 'User Dashboard', and add 4 subtasks with different colored labels/tags to each: Task 1: 'Design layout' → Status: To Do, Task 2: 'Build components' → Status: In Progress, Task 3: 'Handle errors' → Status: Blocked, Task 4: 'Write tests' → Status: Done",
        env_id="taiga",
        start_url=TAIGA_URL,
    ),

    PlatoTask(
        name="create_kanban_user_stories",
        prompt="Create user story 1: 'Fix homepage bug', assign to Sarah, priority: High, description: 'Users are unable to navigate from the homepage on mobile', attachments: (ex. bugs/error calls). Create user story 2: 'SEO Improvements', assign to Michael, priority: Medium, description: 'Improve keyword ranking for product pages', attachments: None",
        env_id="taiga",
        start_url=TAIGA_URL,
    ),

    PlatoTask(
        name="add_tasks_to_stories",
        prompt="Create tasks for each user story: Task 1 for 'Fix homepage bug': 'Debug mobile navigation issue', Task 2 for 'SEO Improvements': 'Update meta tags'. Assign these tasks to self (user of the account)",
        env_id="taiga",
        start_url=TAIGA_URL,
    ),

    PlatoTask(
        name="move_user_stories_across_columns",
        prompt="Drag and drop the Kanban cards to move them through the columns. Move 'Fix homepage bug' from To Do to In Progress, then from Progress to Ready for Review and finally to Done. Ensure the card status and priority are reflected correctly during each iteration of the process",
        env_id="taiga",
        start_url=TAIGA_URL,
    ),
]

# Epic management tasks
epic_management_tasks = [
    PlatoTask(
        name="create_epic_with_stories",
        prompt="Create an Epic (title: 'E-commerce Integration') and develop five stories: product catalog (high priority, status: In Progress, 5 points), cart (medium priority, status: To Do, 3 points), checkout (Highest priority, status: Done, 8 points), reviews (low priority, status: Blocked, 2 points), discounts (Medium priority, status: To Do, 4 points). Link each story to the Epic, and confirm that the Epic progress bar accurately displays the cumulative status and total story points",
        env_id="taiga",
        start_url=TAIGA_URL,
    ),

    PlatoTask(
        name="check_progress_report_bar",
        prompt="Unlink discounts from Epic, and confirm progress drops. Relink and confirm progress recalculates instantly",
        env_id="taiga",
        start_url=TAIGA_URL,
    ),
]

# Task assignment and tracking tasks
task_tracking_tasks = [
    PlatoTask(
        name="time_logging_tests",
        prompt="Log 3h to self on 'Build components', edit the entry to 2.5h and confirm update, delete the time log and confirm removal, confirm Burn Chart updates accurately",
        env_id="taiga",
        start_url=TAIGA_URL,
    ),
]

# Export tasks
export_tasks = [
    PlatoTask(
        name="export_backlog_as_csv",
        prompt="Export the backlog as a CSV file",
        env_id="taiga",
        start_url=TAIGA_URL,
    ),
]

all_tasks = (
    project_setup_tasks + sprint_management_tasks + user_story_tasks +
    epic_management_tasks + task_tracking_tasks + export_tasks
)