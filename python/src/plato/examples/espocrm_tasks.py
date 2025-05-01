import json
from typing import Tuple
from plato.models.task import CustomEvalConfig, MutationVariable, PlatoTask, SemanticMatchVariable, StateMutationMatch, StateMutationMatchEvalConfig
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
        eval_config=StateMutationMatchEvalConfig(
            mutations=[
                StateMutationMatch(
                    tablename="auth_log_record",
                    action="INSERT",
                    values={
                      "deleted": False,
                      "user_id": "680b027de457da0c5",
                      "username": "admin",
                      "is_denied": False,
                      "portal_id": None,
                      "denial_reason": None,
                      "request_method": "GET",
                      "authentication_method": "Espo"
                  }
                ),
                StateMutationMatch(
                    tablename="opportunity",
                    action="INSERT",
                    values={
                      "id": MutationVariable(name="opportunity_id"),
                      "stage": "Qualification",
                      "amount": 45000,
                      "deleted": False,
                      "account_id": "2a9b328d29544b88a",
                      "close_date": "2025-05-15",
                      "contact_id": None,
                      "last_stage": "Qualification",
                      "campaign_id": None,
                      "description": None,
                      "lead_source": None,
                      "probability": 30,
                      "created_by_id": "680b027de457da0c5",
                      "modified_by_id": None,
                      "amount_currency": "USD",
                      "assigned_user_id": "15852d37407e45bab",
                    },
                ),
                StateMutationMatch(
                    tablename="note",
                    action="INSERT",
                    values={
                      "data": "{\"assignedUserId\":\"15852d37407e45bab\",\"assignedUserName\":\"Jason Doyle\",\"statusValue\":\"Qualification\",\"statusField\":\"stage\",\"statusStyle\":\"default\"}",
                      "post": None,
                      "type": "Create",
                      "number": 1,
                      "deleted": False,
                      "is_global": False,
                      "is_pinned": False,
                      "parent_id": MutationVariable(name="opportunity_id"),
                      "related_id": None,
                      "is_internal": False,
                      "parent_type": "Opportunity",
                      "target_type": None,
                      "related_type": None,
                      "created_by_id": "680b027de457da0c5",
                      "modified_by_id": None,
                      "super_parent_id": "2a9b328d29544b88a",
                      "super_parent_type": "Account"
                    },
                ),
                StateMutationMatch(
                    tablename="note_user",
                    action="INSERT",
                    values={
                      "deleted": False,
                      "user_id": "15852d37407e45bab"
                    },
                ),
                StateMutationMatch(
                    tablename="account",
                    action="UPDATE",
                    values={
                      "name": "Frost, Simmons and Blackwell",
                      "type": "Investor",
                      "deleted": False,
                      "website": "http://www.henson.info/",
                      "industry": "Technology",
                      "sic_code": None,
                      "campaign_id": None,
                      "description": "Process Mrs might. Capital north writer move above discuss figure. We box partner south industry public report.",
                      "created_by_id": "ba1345ba10c14590b",
                      "modified_by_id": None,
                      "assigned_user_id": "fed7cbf15f5e4aada",
                      "billing_address_city": "Blackburnmouth",
                      "billing_address_state": "Florida",
                      "shipping_address_city": None,
                      "billing_address_street": "5030 Sherry Summit Apt. 355",
                      "shipping_address_state": None,
                      "billing_address_country": "El Salvador",
                      "shipping_address_street": None,
                      "shipping_address_country": None,
                      "billing_address_postal_code": "17608",
                      "shipping_address_postal_code": None
                    },
                ),
            ],
        ),
    ),
    PlatoTask(
        name="update_opportunity_stage_and_probability_v2",
        prompt="Update the 'Function-based zero-defect standardization' opportunity with Sanchez-Gardner from Qualification stage to Proposal stage and increase the probability from 50% to 70%.",
        env_id="espocrm",
        start_url="http://espocrm.com",
        eval_config=StateMutationMatchEvalConfig(
            mutations=[
                StateMutationMatch(
                    tablename="auth_log_record",
                    action="INSERT",
                    values={
                        "deleted": False,
                        "user_id": "680b027de457da0c5",
                        "username": "admin",
                        "is_denied": False,
                        "portal_id": None,
                        "denial_reason": None,
                        "request_method": "GET",
                        "authentication_method": "Espo"
                    }
                ),
                StateMutationMatch(
                    tablename="opportunity",
                    action="UPDATE",
                    values={
                        "id": "50537be92ef34e6f8",
                        "name": "Function-based zero-defect standardization",
                        "stage": "Proposal",
                        "amount": 72031.44,
                        "deleted": False,
                        "account_id": "14c93a41929243df9",
                        "close_date": "2025-09-22",
                        "contact_id": "b8f11f5440e94ac5b",
                        "last_stage": "Proposal",
                        "campaign_id": None,
                        "description": "Someone drive near those. Bed morning to. Position entire some past management well any.",
                        "lead_source": "Web Site",
                        "probability": 70,
                        "created_by_id": "15852d37407e45bab",
                        "modified_by_id": "680b027de457da0c5",
                        "amount_currency": "USD",
                        "assigned_user_id": "f69beb4defc149fd9"
                    }
                ),
                StateMutationMatch(
                    tablename="note",
                    action="INSERT",
                    values={
                        "id": MutationVariable(name="note_id"),
                        "data": "{\"field\":\"stage\",\"value\":\"Proposal\",\"style\":\"primary\"}",
                        "post": None,
                        "type": "Status",
                        "number": 1,
                        "deleted": False,
                        "is_global": False,
                        "is_pinned": False,
                        "parent_id": "50537be92ef34e6f8",
                        "related_id": None,
                        "is_internal": False,
                        "parent_type": "Opportunity",
                        "target_type": None,
                        "related_type": None,
                        "created_by_id": "680b027de457da0c5",
                        "modified_by_id": None,
                        "super_parent_id": "14c93a41929243df9",
                        "super_parent_type": "Account"
                    }
                ),
                StateMutationMatch(
                    tablename="note_user",
                    action="INSERT",
                    values={
                        "deleted": False,
                        "note_id": MutationVariable(name="note_id"),
                        "user_id": "f69beb4defc149fd9"
                    }
                )
            ]
        )
    ),
    PlatoTask(
        name="update_opportunity_contact_and_amount",
        prompt="Update the 'Quality-focused bandwidth-monitored knowledge user' opportunity with Miller, Mason and Harris by adding a new contact Thomas Wilson as an influencer and changing the amount from $303,248.66 to $325,000.",
        env_id="espocrm",
        start_url="http://espocrm.com",
        eval_config=StateMutationMatchEvalConfig(
            mutations=[
                StateMutationMatch(
                    tablename="auth_log_record",
                    action="INSERT",
                    values={
                        "deleted": False,
                        "user_id": "680b027de457da0c5",
                        "username": "admin",
                        "is_denied": False,
                        "portal_id": None,
                        "denial_reason": None,
                        "request_method": "GET",
                        "authentication_method": "Espo"
                    }
                ),
                StateMutationMatch(
                    tablename="contact",
                    action="INSERT",
                    values={
                        "id": MutationVariable(name="contact_id"),
                        "deleted": False,
                        "last_name": "Wilson",
                        "first_name": "Thomas",
                        "account_id": "e0cc971e38eb48e29", # Miller, Mason and Harris
                        "salutation_name": "Mr.",
                        "created_by_id": "680b027de457da0c5",
                        "modified_by_id": None
                    }
                ),
                StateMutationMatch(
                    tablename="account_contact",
                    action="INSERT",
                    values={
                        "role": None, # Role on account is null
                        "deleted": False,
                        "account_id": "e0cc971e38eb48e29",
                        "contact_id": MutationVariable(name="contact_id"),
                        "is_inactive": False
                    }
                ),
                 StateMutationMatch(
                    tablename="note", # Contact creation note
                    action="INSERT",
                    values={
                        "id": MutationVariable(name="note_id_contact"),
                        "data": "{}",
                        "post": None,
                        "type": "Create",
                        "number": 1,
                        "deleted": False,
                        "is_global": False,
                        "is_pinned": False,
                        "parent_id": MutationVariable(name="contact_id"),
                        "related_id": None,
                        "is_internal": False,
                        "parent_type": "Contact",
                        "target_type": None,
                        "related_type": None,
                        "created_by_id": "680b027de457da0c5",
                        "modified_by_id": None,
                        "super_parent_id": "e0cc971e38eb48e29",
                        "super_parent_type": "Account"
                    }
                 ),
                StateMutationMatch(
                    tablename="account", # Ensure account exists
                    action="UPDATE", # Even though only stream updated, check core fields
                    values={
                      "id": "e0cc971e38eb48e29",
                      "name": "Miller, Mason and Harris",
                      "type": "Reseller",
                      "deleted": False,
                      "website": "http://harper.org/",
                      "industry": "Energy"
                    },
                ),
                StateMutationMatch(
                    tablename="opportunity",
                    action="UPDATE",
                    values={
                        "id": "aa177ada650c43c9a",
                        "name": "Quality-focused bandwidth-monitored knowledge user",
                        "amount": 325000.0, # Assert the specific amount change requested
                        "deleted": False,
                        "account_id": "e0cc971e38eb48e29",
                        "contact_id": "a2931cff08844d64a", # Original contact
                        "lead_source": "Email",
                        "amount_currency": "USD",
                        "modified_by_id": "680b027de457da0c5"
                        # Note: Stage and probability also changed in the data, but not requested in prompt
                    }
                ),
                StateMutationMatch(
                    tablename="contact_opportunity", # Link contact to opportunity
                    action="INSERT",
                    values={
                        "role": "Influencer", # Assert the role specified in prompt
                        "deleted": False,
                        "contact_id": MutationVariable(name="contact_id"),
                        "opportunity_id": "aa177ada650c43c9a"
                    }
                ),
                 StateMutationMatch(
                    tablename="note", # Opportunity update note
                    action="INSERT",
                    values={
                        "id": MutationVariable(name="note_id_opp_update"),
                        "data": "{\"fields\":[\"amount\"],\"attributes\":{\"was\":{\"amountCurrency\":\"USD\",\"amount\":303248.66},\"became\":{\"amountCurrency\":\"USD\",\"amount\":325000}}}",
                        "post": None,
                        "type": "Update",
                        "number": 2,
                        "deleted": False,
                        "is_global": False,
                        "is_pinned": False,
                        "parent_id": "aa177ada650c43c9a",
                        "related_id": None,
                        "is_internal": False,
                        "parent_type": "Opportunity",
                        "target_type": None,
                        "related_type": None,
                        "created_by_id": "680b027de457da0c5",
                        "modified_by_id": None,
                        "super_parent_id": None,
                        "super_parent_type": None
                    }
                 )
            ]
        )
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
        eval_config=StateMutationMatchEvalConfig(
            mutations=[
                StateMutationMatch(
                    tablename="auth_log_record",
                    action="INSERT",
                    values={
                        "deleted": False,
                        "user_id": "680b027de457da0c5", # Assuming admin performs the action
                        "username": "admin",
                        "is_denied": False,
                        "portal_id": None,
                        "denial_reason": None,
                        "request_method": "GET", # Or appropriate method
                        "authentication_method": "Espo"
                    }
                ),
                StateMutationMatch(
                    tablename="contact",
                    action="UPDATE", # Core fields should remain the same
                    values={
                        "id": "1351defd1dd045919",
                        "deleted": False,
                        "last_name": "Huynh",
                        "first_name": "Diana",
                        "account_id": "f8dc614113844eeaa", # Peterson LLC
                        "salutation_name": "Mr.",
                        "modified_by_id": "680b027de457da0c5" # User performing action
                    }
                ),
                StateMutationMatch(
                    tablename="account_contact", # The key role update
                    action="UPDATE",
                    values={
                        "role": "Decision Maker", # Assert the new role
                        "deleted": False,
                        "account_id": "f8dc614113844eeaa", # Peterson LLC
                        "contact_id": "1351defd1dd045919", # Diana Huynh
                        "is_inactive": False
                    }
                ),
                StateMutationMatch(
                    tablename="meeting", # Meeting creation
                    action="INSERT",
                    values={
                        "id": MutationVariable(name="meeting_id"),
                        "name": "Follow-up Meeting with Diana Huynh",
                        "status": "Planned",
                        "deleted": False,
                        "date_start": "2025-04-24T17:00:00", # 10 AM local -> 17:00 UTC
                        "date_end": "2025-04-24T18:00:00",   # Assumes 1 hour meeting
                        "is_all_day": False,
                        "created_by_id": "680b027de457da0c5",
                        "assigned_user_id": "680b027de457da0c5" # Assuming assigned to creator
                    }
                ),
                StateMutationMatch(
                    tablename="contact_meeting", # Link contact to meeting
                    action="INSERT",
                    values={
                        "status": "None",
                        "deleted": False,
                        "contact_id": "1351defd1dd045919", # Diana Huynh
                        "meeting_id": MutationVariable(name="meeting_id")
                    }
                ),
                StateMutationMatch(
                    tablename="meeting_user", # Link user to meeting
                    action="INSERT",
                    values={
                        "status": "Accepted",
                        "deleted": False,
                        "user_id": "680b027de457da0c5", # User performing action
                        "meeting_id": MutationVariable(name="meeting_id")
                    }
                ),
                StateMutationMatch(
                    tablename="note", # Meeting creation note
                    action="INSERT",
                    values={
                        "id": MutationVariable(name="note_id_meeting_create"),
                        "data": "{\"assignedUserId\":\"680b027de457da0c5\",\"assignedUserName\":\"Admin\",\"statusValue\":\"Planned\",\"statusField\":\"status\",\"statusStyle\":\"default\"}",
                        "post": None,
                        "type": "Create",
                        "number": 1,
                        "deleted": False,
                        "is_global": False,
                        "is_pinned": False,
                        "parent_id": MutationVariable(name="meeting_id"),
                        "parent_type": "Meeting",
                        "created_by_id": "680b027de457da0c5"
                    }
                ),
                StateMutationMatch(
                    tablename="note", # CreateRelated note (linking meeting to contact)
                    action="INSERT",
                    values={
                        "id": MutationVariable(name="note_id_create_related"),
                        "data": None,
                        "post": None,
                        "type": "CreateRelated",
                        "number": 2, # Note the number increment
                        "deleted": False,
                        "is_global": False,
                        "is_pinned": False,
                        "parent_id": "1351defd1dd045919", # Diana Huynh
                        "parent_type": "Contact",
                        "related_id": MutationVariable(name="meeting_id"),
                        "related_type": "Meeting",
                        "created_by_id": "680b027de457da0c5"
                    }
                ),
                StateMutationMatch(
                    tablename="note_user", # User for CreateRelated note
                    action="INSERT",
                    values={
                        "deleted": False,
                        "note_id": MutationVariable(name="note_id_create_related"),
                        "user_id": "680b027de457da0c5"
                    }
                )
            ]
        )
    ),
    PlatoTask(
        name="create_new_contact",
        prompt="Create a new contact named Robert Farlow associated with the Green Ltd account, with role 'Technical Contact' and email address robert.farlow@green.com.",
        env_id="espocrm",
        start_url="http://espocrm.com",
        eval_config=StateMutationMatchEvalConfig(
            mutations=[
                StateMutationMatch(
                    tablename="auth_log_record",
                    action="INSERT",
                    values={
                        "deleted": False,
                        "user_id": "680b027de457da0c5",
                        "username": "admin",
                        "is_denied": False,
                        "portal_id": None,
                        "denial_reason": None,
                        "request_method": "GET",
                        "authentication_method": "Espo"
                    }
                ),
                StateMutationMatch(
                    tablename="contact",
                    action="INSERT",
                    values={
                        "id": MutationVariable(name="contact_id"),
                        "deleted": False,
                        "last_name": "Farlow",
                        "first_name": "Robert",
                        "account_id": "8579744dd6d8410d8",
                        "created_by_id": "680b027de457da0c5",
                        "modified_by_id": None
                    }
                ),
                StateMutationMatch(
                    tablename="email_address",
                    action="INSERT",
                    values={
                        "id": MutationVariable(name="email_id"),
                        "name": "robert.farlow@green.com",
                        "lower": "robert.farlow@green.com",
                        "deleted": False,
                        "invalid": False,
                        "opt_out": False
                    }
                ),
                StateMutationMatch(
                    tablename="entity_email_address",
                    action="INSERT",
                    values={
                        "deleted": False,
                        "primary": True,
                        "entity_id": MutationVariable(name="contact_id"),
                        "entity_type": "Contact",
                        "email_address_id": MutationVariable(name="email_id")
                    }
                ),
                StateMutationMatch(
                    tablename="account_contact",
                    action="INSERT",
                    values={
                        "role": "Technical Contact",
                        "deleted": False,
                        "account_id": "8579744dd6d8410d8",
                        "contact_id": MutationVariable(name="contact_id"),
                        "is_inactive": False
                    }
                ),
                StateMutationMatch(
                    tablename="note",
                    action="INSERT",
                    values={
                        "data": "{}",
                        "type": "Create",
                        "deleted": False,
                        "is_global": False,
                        "is_pinned": False,
                        "parent_id": MutationVariable(name="contact_id"),
                        "related_id": None,
                        "is_internal": False,
                        "parent_type": "Contact",
                        "target_type": None,
                        "related_type": None,
                        "created_by_id": "680b027de457da0c5",
                        "modified_by_id": None,
                        "super_parent_id": "8579744dd6d8410d8",
                        "super_parent_type": "Account"
                    }
                )
            ]
        )
    ),
    PlatoTask(
        name="create_new_account_with_note",
        prompt="Create a new account 'Technovate Solutions' with type 'Customer', industry 'Technology', assign it to Cynthia Cuevas, and add a note in the account description that they were referred by the Wagner and Sons account.",
        env_id="espocrm",
        start_url="http://espocrm.com",
        eval_config=StateMutationMatchEvalConfig(
            mutations=[
                 StateMutationMatch(
                    tablename="auth_log_record",
                    action="INSERT",
                    values={
                        "deleted": False,
                        "user_id": "680b027de457da0c5",
                        "username": "admin",
                        "is_denied": False,
                        "portal_id": None,
                        "denial_reason": None,
                        "request_method": "GET",
                        "authentication_method": "Espo"
                    }
                ),
                StateMutationMatch(
                    tablename="account",
                    action="INSERT",
                    values={
                        "id": MutationVariable(name="account_id"),
                        "name": "Technovate Solutions",
                        "type": "Customer",
                        "deleted": False,
                        "website": None,
                        "industry": "Technology",
                        "description": SemanticMatchVariable(description="Referred by the Wagner and Sons account"), # Note text ended up here in data
                        "created_by_id": "680b027de457da0c5",
                        "modified_by_id": None,
                        "assigned_user_id": "6f29af2910204ffbb" # Cynthia Cuevas
                    }
                ),
                 StateMutationMatch(
                    tablename="note", # Account creation note (with assignment info)
                    action="INSERT",
                    values={
                        "id": MutationVariable(name="note_id"),
                        "data": "{\"assignedUserId\":\"6f29af2910204ffbb\",\"assignedUserName\":\"Cynthia Cuevas\"}",
                        "post": None,
                        "type": "Create",
                        "number": 1,
                        "deleted": False,
                        "is_global": False,
                        "is_pinned": False,
                        "parent_id": MutationVariable(name="account_id"),
                        "related_id": None,
                        "is_internal": False,
                        "parent_type": "Account",
                        "target_type": None,
                        "related_type": None,
                        "created_by_id": "680b027de457da0c5",
                        "modified_by_id": None,
                        "super_parent_id": None,
                        "super_parent_type": None
                    }
                 )
            ]
        )
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
        eval_config=StateMutationMatchEvalConfig(
          mutations=[
              StateMutationMatch(
                  tablename="auth_log_record",
                  action="INSERT",
                  values={
                      "deleted": False,
                      "user_id": "680b027de457da0c5",
                      "username": "admin",
                      "is_denied": False,
                      "portal_id": None,
                      "denial_reason": None,
                      "request_method": "GET",
                      "authentication_method": "Espo"
                  }
              ),
              StateMutationMatch(
                  tablename="note",
                  action="INSERT",
                  values={
                      "data": "{}",
                      "post": "Are there any updates on this opportunity?",
                      "type": "Post",
                      "deleted": False,
                      "is_global": False,
                      "is_pinned": False,
                      "parent_id": "981b6365f14f4befa",
                      "related_id": None,
                      "is_internal": False,
                      "parent_type": "Opportunity",
                      "target_type": None,
                      "related_type": None,
                      "created_by_id": "680b027de457da0c5",
                      "modified_by_id": None,
                      "super_parent_id": None,
                      "super_parent_type": None
                  }
              ),
              StateMutationMatch(
                  tablename="opportunity",
                  action="UPDATE",
                  values={
                      "id": "981b6365f14f4befa",
                      "name": "Compatible discrete infrastructure",
                      "stage": "Qualification",
                      "amount": 421657.76,
                      "deleted": False,
                      "amount_currency": "USD"
                  }
              ),
              StateMutationMatch(
                  tablename="note",
                  action="INSERT",
                  values={
                      "data": "{}",
                      "post": "Are there any updates on this opportunity?",
                      "type": "Post",
                      "deleted": False,
                      "is_global": False,
                      "is_pinned": False,
                      "parent_id": "607d6db461c54870a",
                      "related_id": None,
                      "is_internal": False,
                      "parent_type": "Opportunity",
                      "target_type": None,
                      "related_type": None,
                      "created_by_id": "680b027de457da0c5",
                      "modified_by_id": None,
                      "super_parent_id": None,
                      "super_parent_type": None
                  }
              ),
              StateMutationMatch(
                  tablename="opportunity",
                  action="UPDATE",
                  values={
                      "id": "607d6db461c54870a",
                      "name": "Grass-roots reciprocal archive",
                      "stage": "Qualification",
                      "amount": 437089.68,
                      "deleted": False,
                      "amount_currency": "USD"
                  }
              )
          ]
        )
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
          "Accounts with names 'Wagner and Sons' (account_id cdfa988475394882a) and 'Wilson-Olson' (account_id ed05672c90aa47c0b) should have a task regarding updated financial statements for the new fiscal year.",
        ),
      ),
    ),


]


all_tasks = (
    opportunities_tasks + contacts_and_accounts_tasks + leads_tasks + meetings_tasks + settings_tasks + multi_step_tasks
)
