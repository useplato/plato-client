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


# 💼 opportunities
# create opportunity: {opportunity_name} with account {account_name} for ${amount} in stage {stage} with {probability}% probability
# update opportunity: {opportunity_name} from stage {current_stage} to {new_stage}
# update opportunity: {opportunity_name} probability from {current_probability}% to {new_probability}%
# update opportunity: {opportunity_name} amount from ${current_amount} to ${new_amount}
# add contact {contact_name} to opportunity {opportunity_name} with role {role}

opportunities_tasks = [
    PlatoTask(
        name="create_new_opportunity",
        prompt="Create a new opportunity with Frost, Simmons and Blackwell account for $45,000 in the Qualification stage with a 30% probability and assign it to Jason Doyle with a close date of May 15, 2025.",
        env_id="espocrm",
        start_url="http://espocrm.com",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(
                x,
                "There should be a new opportunity with Frost, Simmons and Blackwell account for $45,000 in the Qualification stage with a 30% probability, assigned to Jason Doyle (user id 15852d37407e45bab) with a close date of May 15, 2025.",
            ),
        ),
    ),
    PlatoTask(
        name="update_opportunity_stage_and_probability_v2",
        prompt="Update the 'Function-based zero-defect standardization' opportunity with Sanchez-Gardner from Qualification stage to Proposal stage and increase the probability from 50% to 70%.",
        env_id="espocrm",
        start_url="http://espocrm.com",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(
                x,
                "The 'Function-based zero-defect standardization' opportunity with Sanchez-Gardner should be updated from Qualification stage to Proposal stage and the probability should be increased from 50% to 70%.",
            ),
        ),
    ),
    PlatoTask(
        name="update_opportunity_contact_and_amount",
        prompt="Update the 'Quality-focused bandwidth-monitored knowledge user' opportunity with Miller, Mason and Harris by adding a new contact Thomas Wilson as an influencer and changing the amount from $303,248.66 to $325,000.",
        env_id="espocrm",
        start_url="http://espocrm.com",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(
                x,
                "The 'Quality-focused bandwidth-monitored knowledge user' opportunity with Miller, Mason and Harris should have a new contact Thomas Wilson added as an influencer and the amount should be changed from $303,248.66 to $325,000.",
            ),
        ),
    ),
]


# 🧑‍💼 contacts & accounts
# update contact: {contact_name} role from {current_role} to {new_role} for account {account_name}
# create contact: {firstname} {lastname} with account {account_name}, role {role}, email {email}
# create account: {account_name} with type {type}, industry {industry}, assign to {user}
# add note to account: {account_name} with text {note_text}

contacts_and_accounts_tasks = [
    PlatoTask(
        name="update_contact_role_and_schedule_meeting",
        prompt="Update contact Diana Huynh's role from 'Business Contact' to 'Decision Maker' for the Peterson LLC account and schedule a follow-up meeting for April 24, 2025 at 10:00 AM.",
        env_id="espocrm",
        start_url="http://espocrm.com",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(
                x,
                "Contact Diana Huynh's role should be updated from 'Business Contact' to 'Decision Maker' for the Peterson LLC account and a follow-up meeting should be scheduled for April 24, 2025 at 10:00 AM.",
            ),
        ),
    ),
    PlatoTask(
        name="create_new_contact",
        prompt="Create a new contact named Robert Farlow associated with the Green Ltd account, with role 'Technical Contact' and email address robert.farlow@green.com.",
        env_id="espocrm",
        start_url="http://espocrm.com",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(
                x,
                "There should be a new contact named Robert Farlow associated with the Green Ltd account, with role 'Technical Contact' and email address robert.farlow@green.com.",
            ),
        ),
    ),
    PlatoTask(
        name="create_new_account_with_note",
        prompt="Create a new account 'Technovate Solutions' with type 'Customer', industry 'Technology', assign it to Cynthia Cuevas, and add a note that they were referred by the Wagner and Sons account.",
        env_id="espocrm",
        start_url="http://espocrm.com",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(
                x,
                "There should be a new account 'Technovate Solutions' with type 'Customer', industry 'Technology', assigned to Cynthia Cuevas, with a note that they were referred by the Wagner and Sons account.",
            ),
        ),
    ),
]


# 👤 leads
# convert lead: {lead_name} from status {current_status} to contact with account {account_name}
# change lead status: {lead_name} from {current_status} to {new_status}
# log call for lead: {lead_name} with note {note_text}

leads_tasks = [
    PlatoTask(
        name="convert_lead_to_contact_and_account",
        prompt="Convert lead Michael Diaz from 'New' status to a contact, creating a new account called 'Diaz Enterprises' with industry type 'Technology' and assign both to Adam Dudley.",
        env_id="espocrm",
        start_url="http://espocrm.com",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(
                x,
                "Lead Michael Diaz should be converted from 'New' status to a contact, with a new account called 'Diaz Enterprises' with industry type 'Technology' and both should be assigned to Adam Dudley.",
            ),
        ),
    ),
    PlatoTask(
        name="change_lead_status_and_log_call",
        prompt="Change the status of lead Cynthia Cowan from 'Assigned' to 'In Process' and log a call noting that she requested a product demo next week.",
        env_id="espocrm",
        start_url="http://espocrm.com",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(
                x,
                "The status of lead Cynthia Cowan should be changed from 'Assigned' to 'In Process' and a call should be logged noting that she requested a product demo next week.",
            ),
        ),
    ),
]


# 📅 meetings
# create meeting: {meeting_title} with {contact_name} to discuss opportunity {opportunity_name} on {date} at {time}
# invite attendee: {user_name} to meeting {meeting_title}
# schedule group meeting: {meeting_title} on {date} at {time} with {users} and set priority {priority}

meetings_tasks = [
    PlatoTask(
        name="create_meeting_with_attendee",
        prompt="Create a new meeting with Walter Montgomery to discuss the 'Persevering local forecast' opportunity with Gonzales, George and Guzman on April 23, 2025 at 2:00 PM and invite Ashley Powell as an attendee.",
        env_id="espocrm",
        start_url="http://espocrm.com",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(
                x,
                "There should be a new meeting with Walter Montgomery (user_id aae6f6b05d3d43189) to discuss the 'Persevering local forecast' opportunity with Gonzales, George and Guzman (account_id 6f74727cab6e4bec8) on April 23, 2025 at 2:00 PM (9:00 PM (21:00) UTC) with Ashley Powell (user_id ba1345ba10c14590b) as an attendee.",
            ),
        ),
    ),
    PlatoTask(
        name="schedule_group_meeting",
        prompt="Schedule a group meeting titled 'Q2 Pipeline Review' for April 25, 2025 at 1:00 PM with all users assigned to opportunities in the Proposal/Price Quote stage and mark it as a high priority meeting.",
        env_id="espocrm",
        start_url="http://espocrm.com",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(
                x,
                "There should be a group meeting titled 'Q2 Pipeline Review' scheduled for April 25, 2025 at 1:00 PM (8:00 PM (20:00) UTC) with all users assigned to opportunities in the Proposal/Price Quote stage, marked as a high priority meeting.",
            ),
        ),
    ),
]


settings_tasks = [
    PlatoTask(
        name="set_email_signature",
        prompt="Set your email signature to: 'John Smith\nSales Director\nAcme Corporation\nPhone: (555) 123-4567\nEmail: john.smith@acmecorp.com\nwww.acmecorp.com'",
        env_id="espocrm",
        start_url="http://espocrm.com",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(
                x,
                "Your email signature should be set to: 'John Smith\nSales Director\nAcme Corporation\nPhone: (555) 123-4567\nEmail: john.smith@acmecorp.com\nwww.acmecorp.com'",
            ),
        ),
    ),
    PlatoTask(
        name="change_crm_theme",
        prompt="Change the CRM theme from 'Default (Espo)' to a dark mode theme for this account.",
        env_id="espocrm",
        start_url="http://espocrm.com",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(
                x,
                "The preferences tables should be updated with the CRM theme set to a dark mode theme.",
            ),
        ),
    ),
    PlatoTask(
        name="set_calendar_reminders",
        prompt="Set calendar reminders to send an email 5 minutes before",
        env_id="espocrm",
        start_url="http://espocrm.com",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(
                x,
                "Calendar reminders should be set to send an email 5 minutes before",
            ),
        ),
    ),
]


multi_step_tasks = [
    PlatoTask(
        name="update_customer_accounts_https",
        prompt="Update all Customer-type accounts to change their websites to use HTTPS instead of HTTP.",
        env_id="espocrm",
        start_url="http://espocrm.com",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(
                x,
                "'Burke, Chang and Wolf', 'Davis-Kelly', 'Washington Group', 'Ramos, Tran and David', 'Brooks, Briggs and Aguilar' should have their websites changed to use HTTPS instead of HTTP.",
            ),
        ),
    ),

    PlatoTask(
        name="update_sharon_not_started_tasks",
        prompt="Change the status of all 'Not Started' tasks with 'Urgent' which are assigned to Sharon Martin to 'Started'",
        env_id="espocrm",
        start_url="http://espocrm.com",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(
                x,
                "Tasks with names 'Enviornmental run manager here bring.' and 'Everyone tree job.' should be changed to 'Started'",
            ),
        ),
    ),

    # Reassign all opportunities in the "Perception Analysis" stage from Cynthia Curtis to Adam Dudley and increase their amounts by 5%.
    PlatoTask(
        name="reassign_perception_analysis_opportunities",
        prompt="Reassign all opportunities in the 'Perception Analysis' stage from Cynthia Curtis to Adam Dudley and increase their amounts by 5%.",
        env_id="espocrm",
        start_url="http://espocrm.com",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(
                x,
                "Opportunities with names 'Function-based executive infrastructure', 'Diverse bandwidth-monitored intranet' should be re-assigned from Cynthia Curtis to Adam Dudley and their amounts should be increased by 5%.",
            ),
        ),
    ),

    # Update all contacts associated with "Miller, Mason and Harris" to a new address:
    # 555 Madison Avenue, Suite 1200, New York, NY 10022

    PlatoTask(
      name="update_miller_mason_harris_contacts",
      prompt="Update all contacts associated with 'Miller, Mason and Harris' to have the new address: 555 Madison Avenue, Suite 1200, New York, NY 10022",
      env_id="espocrm",
      start_url="http://espocrm.com",
      eval_config=CustomEvalConfig(
        type="custom",
        score_fn=lambda x: llm_judge_eval_fn(
          x,
          "Abigail Galloway and Ricardo Harrison should have their address updated to '555 Madison Avenue, Suite 1200, New York, NY 10022'",
        ),
      ),
    ),

    # Write a comment on all opportunities in the Qualification stage with amounts over $400,000 asking if there are any updates.

    PlatoTask(
        name="write_comment_on_qualification_opportunities",
        prompt="Write a comment on all opportunities in the 'Qualification' stage with amounts over $400,000 asking if there are any updates.",
        env_id="espocrm",
        start_url="http://espocrm.com",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(
                x,
                "Opportunities with names 'Grass-roots reciprocal archive', 'Compatible discrete infrastructure' should have a comment asking if there are any updates.",
            ),
        ),
    ),

    # Add a task for all Accounts in Singapore to request updated financial statements for the new fiscal year
    PlatoTask(
      name="request_financial_statements_singapore",
      prompt="Add a task for all accounts located in Singapore to request updated financial statements for the new fiscal year. Set the due date for 2 weeks from today.",
      env_id="espocrm",
      start_url="http://espocrm.com",
      eval_config=CustomEvalConfig(
        type="custom",
        score_fn=lambda x: llm_judge_eval_fn(
          x,
          "Accounts with names 'Wagner and Sons' and 'Wilson-Olson' should have a task assigned with the description 'Please send updated financial statements for the new fiscal year'.",
        ),
      ),
    ),


]


all_tasks = (
    opportunities_tasks + contacts_and_accounts_tasks + leads_tasks + meetings_tasks + settings_tasks + multi_step_tasks
)
