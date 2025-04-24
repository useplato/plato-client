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
  return response.choices[0].message.parsed.success, response.choices[0].message.parsed.reason


# 🧑‍💼 contacts & companies
# create contact: {firstname}, {lastname}, {email}, {lifecycle_stage}
# associate contact {name} with company {company_name}
# update contact property: {contact_id} → {property_name} = {value}
# enroll {contact} in workflow {workflow_name}
# create company: {domain}, {industry}, {annual_revenue}
# auto-assign lifecycle stage to {contact} based on {form_submission}
contact_and_company_tasks = [
    PlatoTask(
        name="create_contact_and_company",
        prompt="create a contact and company with the following details: name: Robert Farlow, email: rob@plato.so, company: Plato Technologies, Inc.",
        start_url="https://app-na2.hubspot.com",
        env_id="hubspot",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "There should be a contact and company with the following details: name: Robert Farlow, email: rob@plato.so, company: Plato Technologies, Inc."),
        )
    ),
    PlatoTask(
        name="create_contact_with_lifecycle",
        prompt="create a contact with the following details: firstname: Pranav, lastname: Putta, email: pranav@multion.ai, lifecycle_stage: Marketing Qualified Lead",
        start_url="https://app-na2.hubspot.com",
        env_id="hubspot",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "There should be a contact with firstname: Pranav, lastname: Putta, email: pranav@multion.ai, and lifecycle_stage set to Marketing Qualified Lead"),
        )
    ),
    PlatoTask(
        name="associate_contact_with_company",
        prompt="associate contact Pranav Putta with company Multion AI",
        start_url="https://app-na2.hubspot.com",
        env_id="hubspot",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "Contact Pranav Putta should be associated with company Multion AI"),
        )
    ),
    PlatoTask(
        name="update_contact_property",
        prompt="update contact property for contact Pranav Putta → set job_title = Senior Developer",
        start_url="https://app-na2.hubspot.com",
        env_id="hubspot",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "Contact Pranav Putta should have job_title property set to Senior Developer"),
        )
    ),
    PlatoTask(
        name="enroll_contact_in_workflow",
        prompt="enroll contact michael.brown@tech.com in workflow Lead Nurturing Campaign",
        start_url="https://app-na2.hubspot.com",
        env_id="hubspot",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "Contact michael.brown@tech.com should be enrolled in the Lead Nurturing Campaign workflow"),
        )
    ),
    PlatoTask(
        name="create_company_with_details",
        prompt="create company with domain: innovatech.com, industry: Technology, annual_revenue: 5000000",
        start_url="https://app-na2.hubspot.com",
        env_id="hubspot",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "There should be a company with domain: innovatech.com, industry: Technology, and annual_revenue: 5000000"),
        )
    ),
    PlatoTask(
        name="auto_assign_lifecycle_stage",
        prompt="auto-assign lifecycle stage to contact david@startup.com based on form submission: Enterprise Demo Request",
        start_url="https://app-na2.hubspot.com",
        env_id="hubspot",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "Contact david@startup.com should have lifecycle stage automatically assigned based on Enterprise Demo Request form submission"),
        )
    )
]


# 📝 notes & tasks
# pin a note on {contact_name} with {note_text}
# assign task to {owner_name}: follow up with {contact_name} by {due_date}
# create task from email open alert: {contact_email} opened {email_title}

notes_and_tasks_tasks = [
    PlatoTask(
        name="pin_note_on_contact",
        prompt="pin a note on contact Robert Farlow with the following text: This is a test note.",
        start_url="https://app-na2.hubspot.com",
        env_id="hubspot",
    ),
    PlatoTask(
        name="assign_task_to_contact",
        prompt="assign task to Zach Kreutzjans: follow up with Robert Farlow by June 1st.",
        start_url="https://app-na2.hubspot.com",
        env_id="hubspot",
    ),
    PlatoTask(
        name="create_task_from_email_open_alert",
        prompt="create task from email open alert: rob@plato.so opened email with title: Quarterly Product Update.",
        start_url="https://app-na2.hubspot.com",
        env_id="hubspot",
    ),
]

# 📞 calls & meetings
# log a call: {call_type} with {contact_name} on {call_date}
# record meeting outcome: {contact_name} → {meeting_outcome}

calls_and_meetings_tasks = [
    PlatoTask(
        name="log_call",
        prompt="log a call: phone call with Robert Farlow on June 1st.",
        start_url="https://app-na2.hubspot.com",
        env_id="hubspot",
    ),
    PlatoTask(
        name="record_meeting_outcome",
        prompt="record meeting outcome: Robert Farlow → successful meeting.",
        start_url="https://app-na2.hubspot.com",
        env_id="hubspot",
    ),

]

# 📧 emails & marketing
# send 1:1 tracked email to {contact_name} with template {template_name}
# create & send marketing email: {email_name} to list {list_name}
# set email subscription status for {contact_email} to {opt_in_status}
# track email reply: {contact_email} replied to {email_subject}

emails_and_marketing_tasks = [
    PlatoTask(
        name="send_1_1_tracked_email",
        prompt="send 1:1 tracked email to Robert Farlow with template Quarterly Product Update.",
        start_url="https://app-na2.hubspot.com",
        env_id="hubspot",
    ),
    PlatoTask(
        name="create_and_send_marketing_email",
        prompt="create & send marketing email: Quarterly Product Update to list Test List.",
        start_url="https://app-na2.hubspot.com",
        env_id="hubspot",
    ),
    PlatoTask(
        name="set_email_subscription_status",
        prompt="set email subscription status for rob@plato.so to opt-in.",
        start_url="https://app-na2.hubspot.com",
        env_id="hubspot",
    ),
    PlatoTask(
        name="track_email_reply",
        prompt="track email reply: rob@plato.so replied to Quarterly Product Update.",
        start_url="https://app-na2.hubspot.com",
        env_id="hubspot",
    )
]

# 💼 deals
# create deal: {deal_name}, stage {deal_stage}, value ${amount}
# associate {deal_name} with contact {contact} and company {company}
# move deal {deal_name} to stage {next_stage}
# set close date for {deal_name} to {close_date}

deals_tasks = [
    PlatoTask(
        name="create_and_associate_deal",
        prompt="create deal: Enterprise Software Solution, stage Proposal, value $100000 for company Plato Technologies, Inc. Then associate it with contact Rob Farlow.",
        start_url="https://app-na2.hubspot.com",
        env_id="hubspot",
    ),
    PlatoTask(
        name="move_deal_to_stage",
        prompt="move deal Platform Expansion - Pied Piper to stage Closed Won.",
        start_url="https://app-na2.hubspot.com",
        env_id="hubspot",
    ),
    PlatoTask(
        name="set_close_date_for_deal",
        prompt="set close date for Platform Expansion - Pied Piper to June 1st.",
        start_url="https://app-na2.hubspot.com",
        env_id="hubspot",
    )
]

# ⚙️ automations
# trigger workflow when {property} changes to {value}
# delay workflow for {number} days then send {email_name}
# rotate contact owner for leads in {region}
# if {email_open_rate} < 20%, enroll in {re-engagement_workflow}

automations_tasks = [
    PlatoTask(
        name="trigger_workflow_when_property_changes",
        prompt="trigger workflow when property Lead Score changes to 50.",
        start_url="https://app-na2.hubspot.com",
        env_id="hubspot",
    ),
    PlatoTask(
        name="delay_workflow_for_days",
        prompt="delay workflow for 3 days then send Quarterly Product Update.",
        start_url="https://app-na2.hubspot.com",
        env_id="hubspot",
    ),
    PlatoTask(
        name="rotate_contact_owner_for_leads_in_region",
        prompt="rotate contact owner for leads in New York.",
        start_url="https://app-na2.hubspot.com",
        env_id="hubspot",
    ),
    PlatoTask(
        name="if_email_open_rate_below_20_enroll_in_re_engagement_workflow",
        prompt="if email open rate is below 20%, enroll in Re-Engagement Workflow.",
        start_url="https://app-na2.hubspot.com",
        env_id="hubspot",
    )
]

# 📊 reporting & dashboards
# view sales dashboard: {team_name} - this month's pipeline = ${pipeline_total}
# create report: contacts with {deal_stage} = proposal} in {region}
# export contact list {saved_view_name} to csv

reporting_and_dashboards_tasks = [
    PlatoTask(
        name="view_sales_dashboard",
        prompt="view sales dashboard: Test Team - this month's pipeline = $1000.",
        start_url="https://app-na2.hubspot.com",
        env_id="hubspot",
    ),
    PlatoTask(
        name="create_report",
        prompt="create report: contacts with Proposal in New York.",
        start_url="https://app-na2.hubspot.com",
        env_id="hubspot",
    ),
    PlatoTask(
        name="export_contact_list",
        prompt="export contact list Test Saved View to csv.",
        start_url="https://app-na2.hubspot.com",
        env_id="hubspot",
    )
]

# 📥 forms & lists
# build form: {form_name} with fields {email}, {job_title}, {company_size}
# trigger workflow when {form_name} is submitted
# add {contact} to static list {list_name}
# create smart list: contacts where {lead_score} > 50 and {lifecycle_stage} = MQL

forms_and_lists_tasks = [
    PlatoTask(
        name="form_workflow_and_list_management",
        prompt="build form: Test Form with fields email, job_title, company_size. Then trigger workflow when Test Form is submitted. Finally, add contact Robert Farlow to static list Test List.",
        start_url="https://app-na2.hubspot.com",
        env_id="hubspot",
    ),
    PlatoTask(
        name="create_smart_list",
        prompt="create smart list: contacts where lead_score > 50 and lifecycle_stage = MQL.",
        start_url="https://app-na2.hubspot.com",
        env_id="hubspot",
    )
]



all_tasks = contact_and_company_tasks + notes_and_tasks_tasks + calls_and_meetings_tasks + emails_and_marketing_tasks + deals_tasks + automations_tasks + reporting_and_dashboards_tasks + forms_and_lists_tasks
