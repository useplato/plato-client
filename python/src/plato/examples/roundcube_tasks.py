"""
email_tasks_from_dataset.py
===========================

ExecWebBench – HR-centric e-mail benchmark for Sarah Chen’s mailbox.
All prompts involve ONLY addresses and topics present in the JSON
`user_emails` list supplied on 25 Apr 2025.

• No file-system attachments (links / inline tables instead)
• Tasks grouped by skill category
"""

from __future__ import annotations

import json
from typing import Dict, List, Tuple

from openai import AsyncOpenAI
from pydantic import BaseModel
from plato.models.task import CustomEvalConfig, PlatoTask

# --------------------------------------------------------------------- #
# LLM-as-Judge helper
# --------------------------------------------------------------------- #

client = AsyncOpenAI()


class LLMJudgeResponseFormat(BaseModel):
    success: bool
    reason: str


async def llm_judge_eval_fn(data: dict, prompt: str) -> Tuple[bool, str]:
    """Return (success, reason) for whether *data* satisfies *prompt*."""
    resp = await client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a strict grader.  Respond with JSON "
                    '{\"success\": <bool>, \"reason\": <str>}.'
                ),
            },
            {
                "role": "user",
                "content": f"prompt:\n{prompt}\n\n== agent data ==\n{json.dumps(data)}",
            },
        ],
        response_format=LLMJudgeResponseFormat,
    )
    if getattr(resp.choices[0].message, "parsed", None):
        p = resp.choices[0].message.parsed
        return p.success, p.reason

    txt = resp.choices[0].message.content or ""
    try:
        obj = json.loads(txt)
        return obj.get("success", False), obj.get("reason", "unknown")
    except json.JSONDecodeError:
        return "true" in txt.lower(), txt or "unable to parse"


# --------------------------------------------------------------------- #
# Skill categories
# --------------------------------------------------------------------- #

Skill = str
SKILLS: Dict[Skill, str] = {
    "compose_drafting": "Compose & Rich-Content Drafting",
    "replies_followup": "Replies & Contextual Follow-up",
    "forward_annotation": "Forwarding & Annotation Workflow",
    "contact_mgmt": "Contact & Group Management",
    "foldering_filters": "Foldering, Filters & Search Automation",
    "settings_prefs": "Settings & Preferences",
}

RC = "http://roundcube.com"  # start-URL placeholder

# --------------------------------------------------------------------- #
# A. COMPOSE / DRAFT
# --------------------------------------------------------------------- #

compose_email_tasks: List[PlatoTask] = [
    PlatoTask(
        name="compose_leadership_planning_invite",
        prompt=(
            "Draft an email from Sarah Chen to the leadership team (Michael Rodriguez, "
            "Jennifer Wu, David Patel, Sophia Martinez) proposing three 1-h time slots "
            "next week for the quarterly strategic-planning meeting; include bullet "
            "agenda (hiring plans Q3/Q4, current head-count review, budget)."
        ),
        start_url=RC,
        env_id="roundcube",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda d: llm_judge_eval_fn(
                d,
                (
                    "Email lists three time slots, addresses four leads, bullet agenda "
                    "covers hiring, head-count, budget."
                ),
            ),
        ),
    ),
    PlatoTask(
        name="compose_interview_invite_ryan_henderson",
        prompt=(
            "Send an interview invitation to Ryan Henderson (cc Ethan Brown): outline "
            "on-site schedule (coding, design, culture fit, team meet-and-greet) and "
            "ask for availability next Tue 23 Apr or Thu 25 Apr (morning preferred)."
        ),
        start_url=RC,
        env_id="roundcube",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda d: llm_judge_eval_fn(
                d,
                "Invite lists four interview segments, offers Tue 23 / Thu 25 morning, cc Ethan.",
            ),
        ),
    ),
    PlatoTask(
        name="compose_hr_summit_registration_email",
        prompt=(
            "Compose a note from Sarah Chen to Olivia Taylor & Ethan Brown confirming "
            "group registration for **HR Innovation Summit 2024** (June 12–14). "
            "Include the early-bird 20 % discount link and ask them to confirm travel "
            "arrangements by May 10."
        ),
        start_url=RC,
        env_id="roundcube",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda d: llm_judge_eval_fn(
                d,
                "Email to Olivia & Ethan includes summit link, discount note, asks travel confirmation by 10 May.",
            ),
        ),
    ),
    PlatoTask(
        name="compose_all_hands_reminder",
        prompt=(
            "Draft a reminder to all-employees about the **26 Apr company all-hands** "
            "at 15 :00 (room + Zoom).  Bullet agenda: CEO update, product roadmap, new "
            "hires, Q&A.  Ask staff to post questions in #all-hands-questions Slack by "
            "25 Apr."
        ),
        start_url=RC,
        env_id="roundcube",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda d: llm_judge_eval_fn(
                d,
                "Reminder states 26 Apr 15:00, agenda bullets, Slack question deadline 25 Apr.",
            ),
        ),
    ),
]

# --------------------------------------------------------------------- #
# B. REPLY / FOLLOW-UP
# --------------------------------------------------------------------- #

reply_email_tasks: List[PlatoTask] = [
    PlatoTask(
        name="reply_to_health_insurance_renewal",
        prompt=(
            "Reply to Victoria Adams (Health Plus) cc Benjamin Clark + David Patel: "
            "confirm call Wed next week 14 :00, list two questions about premium "
            "increase and wellness programs, include link to company census file."
        ),
        start_url=RC,
        env_id="roundcube",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda d: llm_judge_eval_fn(
                d,
                "Reply confirms Wed 14:00, asks two questions, includes census link.",
            ),
        ),
    ),
    PlatoTask(
        name="reply_to_engineering_growth_plan",
        prompt=(
            "Reply to Liam Nguyen cc Ethan Brown: accept growth plan, confirm meeting "
            "tomorrow 11 :00, and attach **inline table** (no file) of current vs "
            "target head-count for each role."
        ),
        start_url=RC,
        env_id="roundcube",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda d: llm_judge_eval_fn(
                d,
                "Reply to Liam confirms 11 :00, inline head-count table, cc Ethan.",
            ),
        ),
    ),
    PlatoTask(
        name="reply_to_maternity_leave_request",
        prompt=(
            "Reply to Amelia Robinson: congratulate, outline 16-week paid leave policy, "
            "list paperwork steps, confirm meeting Mon 11 :00."
        ),
        start_url=RC,
        env_id="roundcube",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda d: llm_judge_eval_fn(
                d,
                "Reply congratulates, explains 16-week leave, paperwork, confirms Mon 11 :00.",
            ),
        ),
    ),
    PlatoTask(
        name="reply_to_headspace_question",
        prompt=(
            "Respond to Elijah Wright: explain how to activate company Headspace "
            "subscription (step-by-step), confirm that Mental-Health workshop will be "
            "recorded and link will be shared."
        ),
        start_url=RC,
        env_id="roundcube",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda d: llm_judge_eval_fn(
                d,
                "Reply explains Headspace activation steps, confirms recording availability.",
            ),
        ),
    ),
    PlatoTask(
        name="reply_to_isaac_thank_you",
        prompt=(
            "Reply to Isaac Coleman cc Ethan Brown & Liam Nguyen: thank him, share "
            "timeline (decision by Tue next week) and promise update."
        ),
        start_url=RC,
        env_id="roundcube",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda d: llm_judge_eval_fn(
                d,
                "Reply sets decision timeline Tue next week, thanks Isaac, cc Ethan + Liam.",
            ),
        ),
    ),
    PlatoTask(
        name="reply_to_budget_review_request",
        prompt=(
            "Respond to David Patel: attach inline table (Q1 actual vs budget), preview "
            "Q2–Q4 projections, list three cost drivers (recruiting, HR software, "
            "training)."
        ),
        start_url=RC,
        env_id="roundcube",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda d: llm_judge_eval_fn(
                d,
                "Reply to David includes inline table, Q2–Q4 projection summary, lists three cost drivers.",
            ),
        ),
    ),
]

# --------------------------------------------------------------------- #
# C. FORWARD / ANNOTATION
# --------------------------------------------------------------------- #

forward_email_tasks: List[PlatoTask] = [
    PlatoTask(
        name="forward_hr_summit_invitation",
        prompt=(
            "Forward HR Innovation Summit invite (thread 15) to Olivia Taylor & "
            "Ethan Brown: emphasise 20 % discount deadline **15 May**, ask them to "
            "confirm interest, and bold sessions relevant to AI in recruitment."
        ),
        start_url=RC,
        env_id="roundcube",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda d: llm_judge_eval_fn(
                d,
                "Forward highlights 20 % deadline, bolds AI sessions, asks confirmation.",
            ),
        ),
    ),
]

# --------------------------------------------------------------------- #
# D. CONTACT MANAGEMENT  (only people in dataset)
# --------------------------------------------------------------------- #

contact_management_tasks: List[PlatoTask] = [
    PlatoTask(
        name="add_candidate_contact_ryan_henderson",
        prompt=(
            "Create contact Ryan Henderson – ryan.henderson@gmail.com, mobile "
            "+1-415-555-6789, LinkedIn URL, note 'Senior SWE candidate', groups "
            "'Candidates Q2 2024', 'Potential Hires'."
        ),
        start_url=RC,
        env_id="roundcube",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda d: llm_judge_eval_fn(
                d,
                "Ryan Henderson contact with phone, LinkedIn, note, groups created.",
            ),
        ),
    ),
    PlatoTask(
        name="add_candidate_contact_isaac_coleman",
        prompt=(
            "Add contact Isaac Coleman – isaac.coleman@gmail.com, note 'DevOps candidate', "
            "tag with 6 yrs exp, group 'Candidates Q2 2024'."
        ),
        start_url=RC,
        env_id="roundcube",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda d: llm_judge_eval_fn(
                d,
                "Isaac Coleman contact with note, tag, group created.",
            ),
        ),
    ),
]

# --------------------------------------------------------------------- #
# E. FOLDER / FILTER  (generic – no external names)
# --------------------------------------------------------------------- #

foldering_filter_tasks: List[PlatoTask] = [
    PlatoTask(
        name="create_recruiting_folder_structure",
        prompt=(
            "Under parent folder 'Recruiting 2024' create subfolders "
            "{'Backend SWE', 'Frontend SWE', 'DevOps', 'QA', 'Leadership'}. "
            "Move existing candidate threads (Ryan, Isaac, Cypress) to the "
            "appropriate subfolders."
        ),
        start_url=RC,
        env_id="roundcube",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda d: llm_judge_eval_fn(
                d,
                "Folder tree created and candidate threads moved accordingly.",
            ),
        ),
    ),
    PlatoTask(
        name="set_newsletter_filter",
        prompt=(
            "Filter all mails from newsletter@hrtrends.com to 'Newsletters/HR Trends' "
            "folder and mark low priority."
        ),
        start_url=RC,
        env_id="roundcube",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda d: llm_judge_eval_fn(
                d,
                "Filter exists moving HR Trends newsletter to correct folder with low priority.",
            ),
        ),
    ),
]

# --------------------------------------------------------------------- #
# F. SETTINGS  (unchanged generic)
# --------------------------------------------------------------------- #

settings_pref_tasks: List[PlatoTask] = [
    PlatoTask(
        name="configure_headspace_signature",
        prompt=(
            "Add banner line to Sarah Chen's HTML signature: 'Headspace subscription "
            "available to all employees – ask HR for details'."
        ),
        start_url=RC,
        env_id="roundcube",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda d: llm_judge_eval_fn(
                d,
                "Signature banner about Headspace added.",
            ),
        ),
    ),
]

# --------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------- #

TASK_GROUPS: Dict[Skill, List[PlatoTask]] = {
    "compose_drafting": compose_email_tasks,
    "replies_followup": reply_email_tasks,
    "forward_annotation": forward_email_tasks,
    "contact_mgmt": contact_management_tasks,
    "foldering_filters": foldering_filter_tasks,
    "settings_prefs": settings_pref_tasks,
}

all_tasks: List[PlatoTask] = [
    t for group in TASK_GROUPS.values() for t in group
]

__all__ = ["SKILLS", "TASK_GROUPS", "all_tasks"]