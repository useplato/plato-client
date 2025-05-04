import json
from typing import Tuple
from plato.models.task import EnumMatchVariable, MutationVariable, PlatoTask, SemanticMatchVariable, StateMutationMatch, StateMutationMatchEvalConfig
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
        prompt="Update contact Diana Huynh's role from 'Business Contact' to 'Decision Maker' for the Peterson LLC account and schedule a follow-up 1 hour meeting for April 24, 2025 at 10:00 AM.",
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
                        "name": SemanticMatchVariable(description="something like 'Follow-up Meeting with Diana Huynh'"),
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
                          "account_id": "8579744dd6d8410d8",
                          "first_name": "Robert",
                          "campaign_id": None,
                          "description": None,
                          "do_not_call": False,
                          "middle_name": None,
                          "address_city": None,
                          "address_state": None,
                          "created_by_id": "680b027de457da0c5",
                          "address_street": None,
                          "modified_by_id": None,
                          "address_country": None,
                          "salutation_name": EnumMatchVariable(values=["Mr.", None]),
                          "assigned_user_id": None,
                          "address_postal_code": None
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
                    tablename="entity_email_address",
                    action="UPDATE",
                    values={
                        "primary": False,
                        "entity_id": MutationVariable(name="contact_id"),
                        "entity_type": "Contact",
                        "email_address_id": MutationVariable(name="email_id")
                    }
                ),
                StateMutationMatch(
                    tablename="entity_email_address",
                    action="UPDATE",
                    values={
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
                        "id": MutationVariable(name="note_id"),
                        "data": "{}",
                        "post": None,
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
                ),
                StateMutationMatch(
                    tablename="account",
                    action="UPDATE",
                    values={
                      "id": "8579744dd6d8410d8",
                      "name": "Green Ltd",
                      "type": "Customer",
                      "deleted": False,
                      "website": "https://www.cruz.net/",
                      "industry": "Manufacturing",
                      "sic_code": None,
                      "campaign_id": None,
                      "description": "Anything too bar budget consumer prevent social. Risk design plan those pretty job. Husband against crime develop coach one.",
                      "created_by_id": "93a49f0db93242168",
                      "assigned_user_id": "2d87a39b7bdb419aa",
                      "billing_address_city": "Christophershire",
                      "billing_address_state": "Nebraska",
                      "shipping_address_city": None,
                      "billing_address_street": "7958 Robin Track",
                      "shipping_address_state": None,
                      "billing_address_country": "Mozambique",
                      "shipping_address_street": None,
                      "shipping_address_country": None,
                      "billing_address_postal_code": "30662",
                      "shipping_address_postal_code": None
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
                        "description": SemanticMatchVariable(description="something that mentions referred by the Wagner and Sons account"), # Note text ended up here in data
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
                        "name": "Diaz Enterprises",
                        "type": None, # Not specified in prompt
                        "deleted": False,
                        "website": None,
                        "industry": "Technology", # Aligning with prompt
                        "sic_code": None,
                        "campaign_id": None,
                        "description": None,
                        "created_by_id": "680b027de457da0c5",
                        "modified_by_id": None,
                        "assigned_user_id": "f69beb4defc149fd9", # Adam Dudley
                        "billing_address_city": "Port Jerryport", # From lead data
                        "billing_address_state": "New Jersey", # From lead data
                        "billing_address_street": "65418 Baker Heights", # From lead data
                        "billing_address_country": "Grenada", # From lead data
                        "billing_address_postal_code": "06341" # From lead data
                    }
                ),
                StateMutationMatch(
                    tablename="note", # Account creation note
                    action="INSERT",
                    values={
                        "id": MutationVariable(name="note_id_account_create"),
                        "data": "{\"assignedUserId\":\"f69beb4defc149fd9\",\"assignedUserName\":\"Adam Dudley\"}",
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
                ),
                StateMutationMatch(
                    tablename="contact",
                    action="INSERT",
                    values={
                        "id": MutationVariable(name="contact_id"),
                        "deleted": False,
                        "last_name": "Diaz",
                        "account_id": MutationVariable(name="account_id"),
                        "first_name": "Michael",
                        "campaign_id": None,
                        "description": None,
                        "do_not_call": False,
                        "middle_name": None,
                        "address_city": "Port Jerryport", # From lead data
                        "address_state": "New Jersey", # From lead data
                        "address_street": "65418 Baker Heights", # From lead data
                        "address_country": "Grenada", # From lead data
                        "address_postal_code": "06341", # From lead data
                        "created_by_id": "680b027de457da0c5",
                        "modified_by_id": None,
                        "salutation_name": EnumMatchVariable(values=["Mr.", None]),
                        "assigned_user_id": "f69beb4defc149fd9" # Adam Dudley
                    }
                ),
                StateMutationMatch(
                    tablename="note", # Contact creation note
                    action="INSERT",
                    values={
                        "id": MutationVariable(name="note_id_contact_create"),
                        "data": "{\"assignedUserId\":\"f69beb4defc149fd9\",\"assignedUserName\":\"Adam Dudley\"}",
                        "post": None,
                        "type": "Create",
                        "number": 2, # Note number increment
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
                        "super_parent_id": MutationVariable(name="account_id"),
                        "super_parent_type": "Account"
                    }
                ),
                 StateMutationMatch(
                    tablename="note_user", # Link user to contact creation note
                    action="INSERT",
                    values={
                        "deleted": False,
                        "note_id": MutationVariable(name="note_id_contact_create"),
                        "user_id": "f69beb4defc149fd9" # Adam Dudley
                    }
                 ),
                StateMutationMatch(
                    tablename="account_contact",
                    action="INSERT",
                    values={
                        # "role": None, # Role not specified in prompt
                        "deleted": False,
                        "account_id": MutationVariable(name="account_id"),
                        "contact_id": MutationVariable(name="contact_id"),
                        "is_inactive": False
                    }
                ),
                StateMutationMatch(
                    tablename="lead",
                    action="UPDATE",
                    values={
                        "id": "78cb4af7bea04bd08", # Original Lead ID
                        "status": "Converted",
                        "deleted": False,
                        "modified_by_id": "680b027de457da0c5",
                        "created_account_id": MutationVariable(name="account_id"),
                        "created_contact_id": MutationVariable(name="contact_id"),
                        # converted_at is omitted due to timestamp variability
                    }
                ),
                StateMutationMatch(
                    tablename="note", # Lead status change note
                    action="INSERT",
                    values={
                        "id": MutationVariable(name="note_id_lead_status"),
                        "data": "{\"field\":\"status\",\"value\":\"Converted\",\"style\":\"success\"}",
                        "post": None,
                        "type": "Status",
                        "number": 3, # Note number increment
                        "deleted": False,
                        "is_global": False,
                        "is_pinned": False,
                        "parent_id": "78cb4af7bea04bd08", # Original Lead ID
                        "related_id": None,
                        "is_internal": False,
                        "parent_type": "Lead",
                        "target_type": None,
                        "related_type": None,
                        "created_by_id": "680b027de457da0c5",
                        "modified_by_id": None,
                        "super_parent_id": None,
                        "super_parent_type": None
                    }
                ),
                StateMutationMatch(
                    tablename="email",
                    action="UPDATE",
                    values={
                        "id": "a339b59583c44f889",
                        "parent_id": MutationVariable(name="account_id"),
                        "account_id": MutationVariable(name="account_id"),
                        "parent_type": "Account",
                        "modified_by_id": "680b027de457da0c5"
                    }
                ),
                StateMutationMatch(
                    tablename="email",
                    action="UPDATE",
                    values={
                        "id": "48cdb0b5dffe453c9",
                        "parent_id": MutationVariable(name="account_id"),
                        "account_id": MutationVariable(name="account_id"),
                        "parent_type": "Account",
                        "modified_by_id": "680b027de457da0c5"
                    }
                )
            ]
        )
    ),
    PlatoTask(
        name="change_lead_status_and_log_call",
        prompt="Change the status of lead Cynthia Cowan from 'Assigned' to 'In Process' and log a call with a title and description noting that she requested a product demo next week.",
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
                    "request_method": "GET",
                    "authentication_method": "Espo"
                }
            ),
            StateMutationMatch(
                tablename="lead",
                action="UPDATE",
                values={
                    "id": "a1547d73ae764581b", # Cynthia Cowan
                    "status": "In Process", # Changed from Assigned
                    "deleted": False,
                    "first_name": "Cynthia",
                    "last_name": "Cowan",
                    "modified_by_id": "680b027de457da0c5"
                }
            ),
            StateMutationMatch(
                tablename="note", # Status change note
                action="INSERT",
                values={
                    "id": MutationVariable(name="note_id_status_change"),
                    "data": '{"field":"status","value":"In Process","style":"primary"}',
                    "type": "Status",
                    "deleted": False,
                    "parent_id": "a1547d73ae764581b", # Link to Lead
                    "parent_type": "Lead",
                    "created_by_id": "680b027de457da0c5"
                }
            ),
            StateMutationMatch(
                tablename="call", # Logged call
                action="INSERT",
                values={
                    "id": MutationVariable(name="call_id"),
                    "name": SemanticMatchVariable(description="something like 'Product Demo Request Call'"), # Title reflecting prompt
                    "status": "Held", # Default status for logged past call
                    "deleted": False,
                    "direction": "Outbound",
                    "parent_id": "a1547d73ae764581b", # Link to Lead
                    "parent_type": "Lead",
                    # Description not explicitly captured in DB diff, but title reflects intent
                    "description": SemanticMatchVariable(description="something like 'requested a product demo next week'"),
                    "created_by_id": "680b027de457da0c5",
                    "assigned_user_id": "680b027de457da0c5"
                }
            ),
            StateMutationMatch(
                tablename="call_lead", # Link call to lead
                action="INSERT",
                values={
                    "deleted": False,
                    "call_id": MutationVariable(name="call_id"),
                    "lead_id": "a1547d73ae764581b"
                }
            ),
            StateMutationMatch(
                tablename="call_user", # Link call to user
                action="INSERT",
                values={
                    "status": "Accepted",
                    "deleted": False,
                    "call_id": MutationVariable(name="call_id"),
                    "user_id": "680b027de457da0c5"
                }
            ),
            StateMutationMatch(
                tablename="note", # CreateRelated note for call linkage
                action="INSERT",
                values={
                    "id": MutationVariable(name="note_id_create_related"),
                    "type": "CreateRelated",
                    "deleted": False,
                    "parent_id": "a1547d73ae764581b", # Link to Lead
                    "parent_type": "Lead",
                    "related_id": MutationVariable(name="call_id"), # Link to Call
                    "related_type": "Call",
                    "created_by_id": "680b027de457da0c5"
                }
            ),
            StateMutationMatch(
                tablename="note_user", # Link user to CreateRelated note
                action="INSERT",
                values={
                    "deleted": False,
                    "note_id": MutationVariable(name="note_id_create_related"),
                    "user_id": "680b027de457da0c5"
                }
            ),
            # Optional: Include the second lead update for stream timestamp if desired
            StateMutationMatch(
                tablename="lead",
                action="UPDATE",
                values={
                    "id": "a1547d73ae764581b",
                    # only stream_updated_at changed here
                }
            )
          ]
        )
    ),
]


# 📅 meetings
# create meeting: {meeting_title} with {contact_name} to discuss opportunity {opportunity_name} on {date} at {time}
# invite attendee: {user_name} to meeting {meeting_title}
# schedule group meeting: {meeting_title} on {date} at {time} with {users} and set priority {priority}

meetings_tasks = [
    PlatoTask(
        name="create_meeting_with_attendee",
        prompt="Create a new 1 hour meeting with Walter Montgomery to discuss the 'Persevering local forecast' opportunity with Gonzales, George and Guzman on April 23, 2025 at 2:00 PM and invite Ashley Powell as an attendee.",
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
                    tablename="meeting",
                    action="INSERT",
                    values={
                        "id": MutationVariable(name="meeting_id"),
                        "name": SemanticMatchVariable(description="something like 'Discuss Persevering local forecast opportunity'"),
                        "status": "Planned",
                        "deleted": False,
                        "date_end": "2025-04-23T22:00:00",
                        "join_url": None,
                        "parent_id": "4f2c746b3fd7413c9",
                        "account_id": "6f74727cab6e4bec8",
                        "date_start": "2025-04-23T21:00:00",
                        "is_all_day": False,
                        "description": None,
                        "parent_type": "Opportunity",
                        "created_by_id": "680b027de457da0c5",
                        "modified_by_id": None,
                        "assigned_user_id": "680b027de457da0c5"
                    }
                ),
                StateMutationMatch(
                    tablename="note",
                    action="INSERT",
                    values={
                        "data": "{\"assignedUserId\":\"680b027de457da0c5\",\"assignedUserName\":\"Admin\",\"statusValue\":\"Planned\",\"statusField\":\"status\",\"statusStyle\":\"default\"}",
                        "post": None,
                        "type": "Create",
                        "number": 1,
                        "deleted": False,
                        "is_global": False,
                        "is_pinned": False,
                        "parent_id": MutationVariable(name="meeting_id"),
                        "related_id": None,
                        "is_internal": False,
                        "parent_type": "Meeting",
                        "target_type": None,
                        "related_type": None,
                        "created_by_id": "680b027de457da0c5",
                        "modified_by_id": None,
                        "super_parent_id": "6f74727cab6e4bec8",
                        "super_parent_type": "Account"
                    }
                ),
                StateMutationMatch(
                    tablename="meeting_user",
                    action="INSERT",
                    values={
                        "status": "None",
                        "deleted": False,
                        "user_id": "ba1345ba10c14590b",
                        "meeting_id": MutationVariable(name="meeting_id")
                    }
                ),
                StateMutationMatch(
                    tablename="meeting_user",
                    action="INSERT",
                    values={
                        "status": "Accepted",
                        "deleted": False,
                        "user_id": "680b027de457da0c5",
                        "meeting_id": MutationVariable(name="meeting_id")
                    }
                ),
                StateMutationMatch(
                    tablename="contact_meeting",
                    action="INSERT",
                    values={
                        "status": "None",
                        "deleted": False,
                        "contact_id": "aae6f6b05d3d43189",
                        "meeting_id": MutationVariable(name="meeting_id")
                    }
                ),
                StateMutationMatch(
                    tablename="note_user",
                    action="INSERT",
                    values={
                        "deleted": False,
                        "note_id": MutationVariable(name="note_id_meeting_create"),
                        "user_id": "ba1345ba10c14590b"
                    }
                ),
                StateMutationMatch(
                    tablename="note_user",
                    action="INSERT",
                    values={
                        "deleted": False,
                        "note_id": MutationVariable(name="note_id_meeting_create"),
                        "user_id": "680b027de457da0c5"
                    }
                ),
                StateMutationMatch(
                    tablename="note",
                    action="INSERT",
                    values={
                        "data": None,
                        "post": None,
                        "type": "CreateRelated",
                        "number": 2,
                        "deleted": False,
                        "is_global": False,
                        "is_pinned": False,
                        "parent_id": "4f2c746b3fd7413c9",
                        "related_id": MutationVariable(name="meeting_id"),
                        "is_internal": False,
                        "parent_type": "Opportunity",
                        "target_type": None,
                        "related_type": "Meeting",
                        "created_by_id": "680b027de457da0c5",
                        "modified_by_id": None,
                        "super_parent_id": "6f74727cab6e4bec8",
                        "super_parent_type": "Account"
                    }
                ),
                StateMutationMatch(
                    tablename="note_user",
                    action="INSERT",
                    values={
                        "deleted": False,
                        "note_id": MutationVariable(name="note_id_opp_related"),
                        "user_id": "ba1345ba10c14590b"
                    }
                ),
                StateMutationMatch(
                    tablename="note_user",
                    action="INSERT",
                    values={
                        "deleted": False,
                        "note_id": MutationVariable(name="note_id_opp_related"),
                        "user_id": "680b027de457da0c5"
                    }
                ),
                StateMutationMatch(
                    tablename="note",
                    action="INSERT",
                    values={
                        "data": None,
                        "post": None,
                        "type": "CreateRelated",
                        "number": 3,
                        "deleted": False,
                        "is_global": False,
                        "is_pinned": False,
                        "parent_id": "aae6f6b05d3d43189",
                        "related_id": MutationVariable(name="meeting_id"),
                        "is_internal": False,
                        "parent_type": "Contact",
                        "target_type": None,
                        "related_type": "Meeting",
                        "created_by_id": "680b027de457da0c5",
                        "modified_by_id": None,
                        "super_parent_id": "6f74727cab6e4bec8",
                        "super_parent_type": "Account"
                    }
                ),
                StateMutationMatch(
                    tablename="note_user",
                    action="INSERT",
                    values={
                        "deleted": False,
                        "note_id": MutationVariable(name="note_id_contact_related"),
                        "user_id": "ba1345ba10c14590b"
                    }
                ),
                StateMutationMatch(
                    tablename="note_user",
                    action="INSERT",
                    values={
                        "deleted": False,
                        "note_id": MutationVariable(name="note_id_contact_related"),
                        "user_id": "680b027de457da0c5"
                    }
                ),
                StateMutationMatch(
                    tablename="opportunity",
                    action="UPDATE",
                    values={
                        "id": "4f2c746b3fd7413c9",
                        "name": "Persevering local forecast",
                        "stage": "Proposal",
                        "amount": 292179.69,
                        "deleted": False,
                        "account_id": "6f74727cab6e4bec8",
                        "close_date": "2025-05-03",
                        "contact_id": "fff375f0b25542ab8",
                        "probability": 30,
                        "assigned_user_id": "ba1345ba10c14590b"
                    }
                ),
                StateMutationMatch(
                    tablename="account",
                    action="UPDATE",
                    values={
                        "id": "6f74727cab6e4bec8",
                        "name": "Gonzales, George and Guzman",
                        "type": "Customer",
                        "deleted": False,
                        "website": "https://www.bell.org/",
                        "industry": "Retail"
                    }
                ),
                StateMutationMatch(
                    tablename="contact",
                    action="UPDATE",
                    values={
                        "id": "aae6f6b05d3d43189",
                        "deleted": False,
                        "last_name": "Montgomery",
                        "first_name": "Walter",
                        "account_id": None,
                        "assigned_user_id": "ba1345ba10c14590b"
                    }
                )
          ]
        )
    ),
    PlatoTask(
        name="schedule_group_meeting",
        prompt="Schedule a 30 minute group meeting titled 'Q2 Pipeline Review' for April 25, 2025 at 1:00 PM with all users assigned to opportunities in the Proposal stage and mark it as a high priority meeting.",
        env_id="espocrm",
        start_url="http://espocrm.com",
        eval_config=StateMutationMatchEvalConfig(
          mutations=[
              StateMutationMatch(
                  tablename="auth_log_record",
                  action="INSERT",
                  values={
                      # id is generated, excluded for matching
                      "deleted": False,
                      "user_id": "680b027de457da0c5",
                      "username": "admin",
                      "is_denied": False,
                      "portal_id": None,
                      # created_at excluded
                      # ip_address, request_url, request_time, auth_token_id excluded (dynamic)
                      "denial_reason": None,
                      "request_method": "GET",
                      "authentication_method": "Espo"
                  }
              ),
              StateMutationMatch(
                  tablename="meeting",
                  action="INSERT",
                  values={
                      "id": MutationVariable(name="meeting_id"),
                      "uid": MutationVariable(name="meeting_uid"),
                      "name": SemanticMatchVariable(description="something like 'Q2 Pipeline Review'"),
                      "status": "Planned",
                      "deleted": False,
                      "date_end": "2025-04-25T20:30:00",
                      "join_url": None,
                      "parent_id": None,
                      "account_id": None,
                      # created_at excluded
                      "date_start": "2025-04-25T20:00:00",
                      "is_all_day": False,
                      "description": None,
                      # modified_at excluded
                      "parent_type": None,
                      "created_by_id": "680b027de457da0c5",
                      "date_end_date": None,
                      "modified_by_id": None,
                      "date_start_date": None,
                      "assigned_user_id": "680b027de457da0c5",
                      # stream_updated_at excluded
                  }
              ),
              StateMutationMatch(
                  tablename="meeting_user",
                  action="INSERT",
                  values={
                      # id is auto-increment, excluded for matching
                      "status": "None",
                      "deleted": False,
                      "user_id": "15852d37407e45bab", # User 1 assigned to Proposal Opps
                      "meeting_id": MutationVariable(name="meeting_id")
                  }
              ),
              StateMutationMatch(
                  tablename="meeting_user",
                  action="INSERT",
                  values={
                      # id is auto-increment, excluded for matching
                      "status": "None",
                      "deleted": False,
                      "user_id": "fed7cbf15f5e4aada", # User 2 assigned to Proposal Opps
                      "meeting_id": MutationVariable(name="meeting_id")
                  }
              ),
              StateMutationMatch(
                  tablename="meeting_user",
                  action="INSERT",
                  values={
                      # id is auto-increment, excluded for matching
                      "status": "Accepted", # Meeting creator (admin) auto-accepts
                      "deleted": False,
                      "user_id": "680b027de457da0c5",
                      "meeting_id": MutationVariable(name="meeting_id")
                  }
              ),
              StateMutationMatch(
                  tablename="note",
                  action="INSERT",
                  values={
                      "id": MutationVariable(name="note_id"),
                      "data": "{\"assignedUserId\":\"680b027de457da0c5\",\"assignedUserName\":\"Admin\",\"statusValue\":\"Planned\",\"statusField\":\"status\",\"statusStyle\":\"default\"}",
                      "post": None,
                      "type": "Create",
                      "number": 1,
                      "deleted": False,
                      "is_global": False,
                      "is_pinned": False,
                      "parent_id": MutationVariable(name="meeting_id"),
                      # created_at excluded
                      "related_id": None,
                      "is_internal": False,
                      # modified_at excluded
                      "parent_type": "Meeting",
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


settings_tasks = [
    PlatoTask(
        name="set_email_signature",
        prompt="Set your email signature to: 'John Smith\\nSales Director\\nAcme Corporation\\nPhone: (555) 123-4567\\nEmail: john.smith@acmecorp.com\\nwww.acmecorp.com'",
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
                    tablename="preferences",
                    action="INSERT", # Or UPDATE if preferences already existed
                    # Using SemanticMatchVariable as the exact JSON might vary slightly
                    # besides the signature itself. The key is verifying the signature part.
                    values={
                      "data": SemanticMatchVariable(description="String containing this information: {\"timeZone\":null,\"dateFormat\":null,\"timeFormat\":null,\"weekStart\":-1,\"defaultCurrency\":null,\"thousandSeparator\":\",\",\"decimalMark\":\".\",\"dashboardLayout\":[{\"name\":\"My Espo\",\"layout\":[{\"id\":\"default-stream\",\"name\":\"Stream\",\"x\":0,\"y\":0,\"width\":2,\"height\":4},{\"id\":\"default-activities\",\"name\":\"Activities\",\"x\":2,\"y\":2,\"width\":2,\"height\":4}]}],\"dashletsOptions\":{},\"dashboardLocked\":false,\"language\":null,\"exportDelimiter\":\",\",\"receiveAssignmentEmailNotifications\":true,\"receiveMentionEmailNotifications\":true,\"receiveStreamEmailNotifications\":true,\"assignmentNotificationsIgnoreEntityTypeList\":[],\"reactionNotifications\":true,\"signature\":\"<p>John Smith</p><p>Sales Director</p><p>Acme Corporation</p><p>Phone: (555) 123-4567</p><p>Email: john.smith@acmecorp.com</p><p>www.acmecorp.com</p>\",\"defaultReminders\":[],\"defaultRemindersTask\":[],\"theme\":null,\"themeParams\":{},\"useCustomTabList\":false,\"addCustomTabs\":false,\"emailReplyToAllByDefault\":true,\"emailReplyForceHtml\":true,\"doNotFillAssignedUserIfNotRequired\":true,\"followEntityOnStreamPost\":true,\"followCreatedEntities\":false,\"followCreatedEntityTypeList\":[],\"emailUseExternalClient\":false,\"scopeColorsDisabled\":false,\"tabColorsDisabled\":false,\"textSearchStoringDisabled\":false,\"calendarSlotDuration\":null,\"calendarScrollHour\":null} plus an 'id' field which doesn't matter.")
                    }
                )
          ]
        )
    ),
    PlatoTask(
        name="change_crm_theme",
        prompt="Change the CRM theme from 'Default (Espo)' to a dark mode theme for this account.",
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
                    tablename="preferences",
                    action="INSERT", # This assumes preferences didn't exist. Could be UPDATE.
                    values={
                        "id": "680b027de457da0c5",
                        "data": '{\n    "id": "680b027de457da0c5",\n    "timeZone": null,\n    "dateFormat": null,\n    "timeFormat": null,\n    "weekStart": -1,\n    "defaultCurrency": null,\n    "thousandSeparator": ",",\n    "decimalMark": ".",\n    "dashboardLayout": [\n        {\n            "name": "My Espo",\n            "layout": [\n                {\n                    "id": "default-stream",\n                    "name": "Stream",\n                    "x": 0,\n                    "y": 0,\n                    "width": 2,\n                    "height": 4\n                },\n                {\n                    "id": "default-activities",\n                    "name": "Activities",\n                    "x": 2,\n                    "y": 2,\n                    "width": 2,\n                    "height": 4\n                }\n            ]\n        }\n    ],\n    "dashletsOptions": {},\n    "dashboardLocked": false,\n    "language": null,\n    "exportDelimiter": ",",\n    "receiveAssignmentEmailNotifications": true,\n    "receiveMentionEmailNotifications": true,\n    "receiveStreamEmailNotifications": true,\n    "assignmentNotificationsIgnoreEntityTypeList": [],\n    "reactionNotifications": true,\n    "signature": null,\n    "defaultReminders": [],\n    "defaultRemindersTask": [],\n    "theme": "Dark",\n    "themeParams": {\n        "navbar": "side"\n    },\n    "useCustomTabList": false,\n    "addCustomTabs": false,\n    "emailReplyToAllByDefault": true,\n    "emailReplyForceHtml": true,\n    "doNotFillAssignedUserIfNotRequired": true,\n    "followEntityOnStreamPost": true,\n    "followCreatedEntities": false,\n    "followCreatedEntityTypeList": [],\n    "emailUseExternalClient": false,\n    "scopeColorsDisabled": false,\n    "tabColorsDisabled": false,\n    "textSearchStoringDisabled": false,\n    "calendarSlotDuration": null,\n    "calendarScrollHour": null\n}'
                    }
                ),
            ]
        )
    ),
    PlatoTask(
        name="set_calendar_reminders",
        prompt="Set default calendar reminders to send an email 5 minutes before",
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
                    tablename="preferences",
                    action="INSERT", # Or UPDATE if preferences already existed
                    values={
                        "id": "680b027de457da0c5",
                        "data": '{\n    "id": "680b027de457da0c5",\n    "timeZone": null,\n    "dateFormat": null,\n    "timeFormat": null,\n    "weekStart": -1,\n    "defaultCurrency": null,\n    "thousandSeparator": ",",\n    "decimalMark": ".",\n    "dashboardLayout": [\n        {\n            "name": "My Espo",\n            "layout": [\n                {\n                    "id": "default-stream",\n                    "name": "Stream",\n                    "x": 0,\n                    "y": 0,\n                    "width": 2,\n                    "height": 4\n                },\n                {\n                    "id": "default-activities",\n                    "name": "Activities",\n                    "x": 2,\n                    "y": 2,\n                    "width": 2,\n                    "height": 4\n                }\n            ]\n        }\n    ],\n    "dashletsOptions": {},\n    "dashboardLocked": false,\n    "language": null,\n    "exportDelimiter": ",",\n    "receiveAssignmentEmailNotifications": true,\n    "receiveMentionEmailNotifications": true,\n    "receiveStreamEmailNotifications": true,\n    "assignmentNotificationsIgnoreEntityTypeList": [],\n    "reactionNotifications": true,\n    "signature": null,\n    "defaultReminders": [\n        {\n            "type": "Email",\n            "seconds": 300\n        }\n    ],\n    "defaultRemindersTask": [],\n    "theme": null,\n    "themeParams": {},\n    "useCustomTabList": false,\n    "addCustomTabs": false,\n    "emailReplyToAllByDefault": true,\n    "emailReplyForceHtml": true,\n    "doNotFillAssignedUserIfNotRequired": true,\n    "followEntityOnStreamPost": true,\n    "followCreatedEntities": false,\n    "followCreatedEntityTypeList": [],\n    "emailUseExternalClient": false,\n    "scopeColorsDisabled": false,\n    "tabColorsDisabled": false,\n    "textSearchStoringDisabled": false,\n    "calendarSlotDuration": null,\n    "calendarScrollHour": null\n}'
                    }
                )
            ]
        )
    ),
]


multi_step_tasks = [
    PlatoTask(
        name="update_customer_accounts_https",
        prompt="Update all Customer-type accounts to change their websites to use HTTPS instead of HTTP.",
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
                    action="UPDATE",
                    values={
                        "id": "ac852a523e864db28",
                        "name": "Brooks, Briggs and Aguilar",
                        "type": "Customer",
                        "deleted": False,
                        "website": "chambers.com", # Updated to HTTPS
                        "industry": "Education",
                        "assigned_user_id": "fed7cbf15f5e4aada",
                        "billing_address_city": "New Michaelbury",
                        "billing_address_state": "Arizona",
                        "billing_address_street": "861 Baker Drive Apt. 615",
                        "billing_address_country": "Sudan",
                        "billing_address_postal_code": "60496",
                    }
                ),
                StateMutationMatch(
                    tablename="account",
                    action="UPDATE",
                    values={
                        "id": "8d9091d9614c4c6fa",
                        "name": "Ramos, Tran and David",
                        "type": "Customer",
                        "deleted": False,
                        "website": "www.harris-blanchard.info", # Updated to HTTPS
                        "industry": "Banking",
                        "assigned_user_id": "2d87a39b7bdb419aa",
                        "billing_address_city": "South Thomas",
                        "billing_address_state": "Ohio",
                        "billing_address_street": "64580 Lisa Ville",
                        "billing_address_country": "Burkina Faso",
                        "billing_address_postal_code": "25175",
                    }
                ),
                StateMutationMatch(
                    tablename="account",
                    action="UPDATE",
                    values={
                        "id": "43564498bb34431b8",
                        "name": "Davis-Kelly",
                        "type": "Customer",
                        "deleted": False,
                        "website": "harmon.info", # Updated to HTTPS
                        "industry": "Banking",
                        "assigned_user_id": "2d87a39b7bdb419aa",
                        "billing_address_city": "South Sue",
                        "billing_address_state": "Delaware",
                        "billing_address_street": "825 Randall Pines Apt. 284",
                        "billing_address_country": "Turkmenistan",
                        "billing_address_postal_code": "31710",
                    }
                ),
                StateMutationMatch(
                    tablename="account",
                    action="UPDATE",
                    values={
                        "id": "4335064565f44052a",
                        "name": "Burke, Chang and Wolf",
                        "type": "Customer",
                        "deleted": False,
                        "website": "oliver-watkins.info", # Updated to HTTPS
                        "industry": "Technology",
                        "assigned_user_id": "93a49f0db93242168",
                        "billing_address_city": "Lake Jason",
                        "billing_address_state": "South Dakota",
                        "billing_address_street": "896 Jones Canyon Apt. 161",
                        "billing_address_country": "Latvia",
                        "billing_address_postal_code": "32348",
                    }
                ),
                StateMutationMatch(
                    tablename="account",
                    action="UPDATE",
                    values={
                        "id": "6a7ed3ef57ab4d9f9",
                        "name": "Washington Group",
                        "type": "Customer",
                        "deleted": False,
                        "website": "villarreal.info", # Updated to HTTPS
                        "industry": "Education",
                        "assigned_user_id": "dbf3c6eb6e6b49e49",
                        "billing_address_city": "North Robin",
                        "billing_address_state": "Colorado",
                        "billing_address_street": "484 Shelly Street",
                        "billing_address_country": "Eritrea",
                        "billing_address_postal_code": "44658",
                    }
                ),
            ]
        )
    ),

    PlatoTask(
        name="update_sharon_not_started_tasks",
        prompt="Change the status of all 'Not Started' tasks with 'Urgent' which are assigned to Sharon Martin to 'Started'",
        env_id="espocrm",
        start_url="http://espocrm.com",
        eval_config=StateMutationMatchEvalConfig(
            mutations=[
                StateMutationMatch(
                    tablename="auth_log_record",
                    action="INSERT",
                    values={
                      "deleted": False,
                      "user_id": "680b027de457da0c5", # admin user
                      "username": "admin",
                      "is_denied": False,
                      "portal_id": None,
                      "denial_reason": None,
                      "request_method": "GET",
                      "authentication_method": "Espo"
                    }
                ),
                StateMutationMatch(
                    tablename="task",
                    action="UPDATE",
                    values={
                      "id": "53db49f3a6ab48918", # Added ID here to identify the record
                      "name": "Everyone tree job.",
                      "status": "Started", # Updated from "Not Started"
                      "deleted": False,
                      "priority": "Urgent",
                      "parent_id": "434c7d7d99bc4ae38",
                      "parent_type": "Opportunity",
                      "assigned_user_id": "dbf3c6eb6e6b49e49" # Assumed Sharon Martin based on prompt
                    }
                ),
                StateMutationMatch(
                    tablename="note",
                    action="INSERT",
                    values={
                      "data": "{\"field\":\"status\",\"value\":\"Started\",\"style\":\"primary\"}",
                      "post": None,
                      "type": "Status",
                      "number": 1,
                      "deleted": False,
                      "is_global": False,
                      "is_pinned": False,
                      "parent_id": "53db49f3a6ab48918", # Related Task ID
                      "is_internal": False,
                      "parent_type": "Task",
                      "target_type": None,
                      "related_type": None,
                      "created_by_id": "680b027de457da0c5" # Admin user
                    }
                ),
                StateMutationMatch(
                    tablename="task",
                    action="UPDATE",
                    values={
                      "id": "245acf70b2ca4f1c9", # Added ID here to identify the record
                      "name": "Environmental run manager here bring.",
                      "status": "Started", # Updated from "Not Started"
                      "deleted": False,
                      "priority": "Urgent",
                      "parent_id": "be05e7de648c49fd9",
                      "parent_type": "Contact",
                      "assigned_user_id": "dbf3c6eb6e6b49e49" # Assumed Sharon Martin based on prompt
                    }
                ),
                StateMutationMatch(
                    tablename="note",
                    action="INSERT",
                    values={
                      "data": "{\"field\":\"status\",\"value\":\"Started\",\"style\":\"primary\"}",
                      "post": None,
                      "type": "Status",
                      "number": 2,
                      "deleted": False,
                      "is_global": False,
                      "is_pinned": False,
                      "parent_id": "245acf70b2ca4f1c9", # Related Task ID
                      "is_internal": False,
                      "parent_type": "Task",
                      "target_type": None,
                      "related_type": None,
                      "created_by_id": "680b027de457da0c5" # Admin user
                    }
                )
            ]
        ),
    ),

    # Reassign all opportunities in the "Perception Analysis" stage from Cynthia Curtis to Adam Dudley and increase their amounts by 5%.
    PlatoTask(
        name="reassign_cynthia_curtis_prospecting_opportunities",
        prompt="Reassign all of Cynthia Curtis's opportunities in the Prospecting stage to Adam Dudley and increase their amounts by 5%.",
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
                        "id": "27136760ec2646bfb",
                        "name": "Customizable content-based complexity",
                        "stage": "Prospecting",
                        "amount": 54381.42,
                        "deleted": False,
                        "account_id": "37afc36368524354b",
                        "close_date": "2025-01-03",
                        "contact_id": "3a12f72f4a42488da",
                        "probability": 10,
                        "modified_by_id": "680b027de457da0c5",
                        "amount_currency": "USD",
                        "assigned_user_id": "f69beb4defc149fd9"
                    }
                ),
                StateMutationMatch(
                    tablename="note",
                    action="INSERT",
                    values={
                        "data": "{\"assignedUserId\":\"f69beb4defc149fd9\",\"assignedUserName\":\"Adam Dudley\"}",
                        "post": None,
                        "type": "Assign",
                        "deleted": False,
                        "is_global": False,
                        "is_pinned": False,
                        "parent_id": "27136760ec2646bfb",
                        "related_id": None,
                        "is_internal": False,
                        "parent_type": "Opportunity",
                        "target_type": None,
                        "related_type": None,
                        "created_by_id": "680b027de457da0c5",
                        "super_parent_id": "37afc36368524354b",
                        "super_parent_type": "Account"
                    }
                ),
                StateMutationMatch(
                    tablename="note_user",
                    action="INSERT",
                    values={
                        "deleted": False,
                        "note_id": MutationVariable(name="note_id_1"),
                        "user_id": "f69beb4defc149fd9"
                    }
                ),
                StateMutationMatch(
                    tablename="note",
                    action="INSERT",
                    values={
                        "data": "{\"fields\":[\"amount\"],\"attributes\":{\"was\":{\"amountCurrency\":\"USD\",\"amount\":51791.83},\"became\":{\"amountCurrency\":\"USD\",\"amount\":54381.42}}}",
                        "post": None,
                        "type": "Update",
                        "deleted": False,
                        "is_global": False,
                        "is_pinned": False,
                        "parent_id": "27136760ec2646bfb",
                        "related_id": None,
                        "is_internal": False,
                        "parent_type": "Opportunity",
                        "target_type": None,
                        "related_type": None,
                        "created_by_id": "680b027de457da0c5"
                    }
                ),
                StateMutationMatch(
                    tablename="opportunity",
                    action="UPDATE",
                    values={
                        "id": "f48d4f7164714fccb",
                        "name": "Future-proofed 5thgeneration analyzer",
                        "stage": "Prospecting",
                        "amount": 48388.83,
                        "deleted": False,
                        "account_id": "4335064565f44052a",
                        "close_date": "2024-05-21",
                        "contact_id": "d1a4ebdf4ba948589",
                        "probability": 10,
                        "modified_by_id": "680b027de457da0c5",
                        "amount_currency": "USD",
                        "assigned_user_id": "f69beb4defc149fd9"
                    }
                ),
                StateMutationMatch(
                    tablename="note",
                    action="INSERT",
                    values={
                        "data": "{\"assignedUserId\":\"f69beb4defc149fd9\",\"assignedUserName\":\"Adam Dudley\"}",
                        "post": None,
                        "type": "Assign",
                        "deleted": False,
                        "is_global": False,
                        "is_pinned": False,
                        "parent_id": "f48d4f7164714fccb",
                        "related_id": None,
                        "is_internal": False,
                        "parent_type": "Opportunity",
                        "target_type": None,
                        "related_type": None,
                        "created_by_id": "680b027de457da0c5",
                        "super_parent_id": "4335064565f44052a",
                        "super_parent_type": "Account"
                    }
                ),
                StateMutationMatch(
                    tablename="note_user",
                    action="INSERT",
                    values={
                        "deleted": False,
                        "note_id": MutationVariable(name="note_id_2"),
                        "user_id": "f69beb4defc149fd9"
                    }
                ),
                StateMutationMatch(
                    tablename="note",
                    action="INSERT",
                    values={
                        "data": "{\"fields\":[\"amount\"],\"attributes\":{\"was\":{\"amountCurrency\":\"USD\",\"amount\":46084.6},\"became\":{\"amountCurrency\":\"USD\",\"amount\":48388.83}}}",
                        "post": None,
                        "type": "Update",
                        "deleted": False,
                        "is_global": False,
                        "is_pinned": False,
                        "parent_id": "f48d4f7164714fccb",
                        "related_id": None,
                        "is_internal": False,
                        "parent_type": "Opportunity",
                        "target_type": None,
                        "related_type": None,
                        "created_by_id": "680b027de457da0c5"
                    }
                ),
                StateMutationMatch(
                    tablename="opportunity",
                    action="UPDATE",
                    values={
                        "id": "bc6216b1d9ee4769a",
                        "name": "Function-based multi-tasking attitude",
                        "stage": "Prospecting",
                        "amount": 343399.42,
                        "deleted": False,
                        "account_id": "bb234c633c69430e8",
                        "close_date": "2024-02-26",
                        "contact_id": "9b7b3961c68a4c76b",
                        "probability": 10,
                        "modified_by_id": "680b027de457da0c5",
                        "amount_currency": "USD",
                        "assigned_user_id": "f69beb4defc149fd9"
                    }
                ),
                StateMutationMatch(
                    tablename="note",
                    action="INSERT",
                    values={
                        "data": "{\"assignedUserId\":\"f69beb4defc149fd9\",\"assignedUserName\":\"Adam Dudley\"}",
                        "post": None,
                        "type": "Assign",
                        "deleted": False,
                        "is_global": False,
                        "is_pinned": False,
                        "parent_id": "bc6216b1d9ee4769a",
                        "related_id": None,
                        "is_internal": False,
                        "parent_type": "Opportunity",
                        "target_type": None,
                        "related_type": None,
                        "created_by_id": "680b027de457da0c5",
                        "super_parent_id": "bb234c633c69430e8",
                        "super_parent_type": "Account"
                    }
                ),
                StateMutationMatch(
                    tablename="note_user",
                    action="INSERT",
                    values={
                        "deleted": False,
                        "note_id": MutationVariable(name="note_id_3"),
                        "user_id": "f69beb4defc149fd9"
                    }
                ),
                StateMutationMatch(
                    tablename="note",
                    action="INSERT",
                    values={
                        "data": "{\"fields\":[\"amount\"],\"attributes\":{\"was\":{\"amountCurrency\":\"USD\",\"amount\":327047.07},\"became\":{\"amountCurrency\":\"USD\",\"amount\":343399.42}}}",
                        "post": None,
                        "type": "Update",
                        "deleted": False,
                        "is_global": False,
                        "is_pinned": False,
                        "parent_id": "bc6216b1d9ee4769a",
                        "related_id": None,
                        "is_internal": False,
                        "parent_type": "Opportunity",
                        "target_type": None,
                        "related_type": None,
                        "created_by_id": "680b027de457da0c5"
                    }
                )
            ]
        )
    ),

    # Update all contacts associated with "Miller, Mason and Harris" to a new address:
    # 555 Madison Avenue, Suite 1200, New York, NY 10022

    PlatoTask(
      name="update_miller_mason_harris_contacts",
      prompt="Update all contacts associated with 'Miller, Mason and Harris' to have the new address: 555 Madison Avenue, Suite 1200, New York, NY 10022",
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
                action="UPDATE",
                values={
                    "id": "8a884b6c6ebd490aa",
                    "deleted": False,
                    "last_name": "Harrison",
                    "account_id": "e0cc971e38eb48e29",
                    "first_name": "Ricardo",
                    "address_city": "New York",
                    "address_state": SemanticMatchVariable(description="NY or New York"),
                    "address_street": "555 Madison Avenue, Suite 1200",
                    "modified_by_id": "680b027de457da0c5",
                    "address_country": SemanticMatchVariable(description="United States, US, USA, etc"),
                    "address_postal_code": "10022"
                }
            ),
            StateMutationMatch(
                tablename="contact",
                action="UPDATE",
                values={
                    "id": "a2931cff08844d64a",
                    "deleted": False,
                    "last_name": "Galloway",
                    "account_id": "e0cc971e38eb48e29",
                    "first_name": "Abigail",
                    "address_city": "New York",
                    "address_state": SemanticMatchVariable(description="NY or New York"),
                    "address_street": "555 Madison Avenue, Suite 1200",
                    "modified_by_id": "680b027de457da0c5",
                    "address_country": SemanticMatchVariable(description="United States, US, USA, etc"),
                    "address_postal_code": "10022"
                }
            )
        ]
      )
    ),

    # Write a comment on all opportunities in the Qualification stage with amounts over $400,000 asking if there are any updates.

    PlatoTask(
        name="write_comments_on_qualification_opportunities",
        prompt="Write a comment on opportunities in the Qualification stage with amounts over $400,000 asking if there are any updates.",
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
                # Opportunity 1: "Diverse regional hierarchy"
                StateMutationMatch(
                    tablename="opportunity",
                    action="UPDATE",
                    values={
                        "id": "1bc5e158e16946a3a",
                        "name": "Diverse regional hierarchy",
                        "stage": "Qualification",
                        "amount": 482038.88,
                        "deleted": False,
                        "amount_currency": "USD"
                    }
                ),
                StateMutationMatch(
                    tablename="note",
                    action="INSERT",
                    values={
                        "data": "{}",
                        "post": SemanticMatchVariable(description="question asking if there are any updates"),
                        "type": "Post",
                        "deleted": False,
                        "is_global": False,
                        "is_pinned": False,
                        "parent_id": "1bc5e158e16946a3a",
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
                # Opportunity 2: "Reverse-engineered mission-critical process improvement"
                StateMutationMatch(
                    tablename="opportunity",
                    action="UPDATE",
                    values={
                        "id": "3ac031b6dd8847cbb",
                        "name": "Reverse-engineered mission-critical process improvement",
                        "stage": "Qualification",
                        "amount": 468546.6,
                        "deleted": False,
                        "amount_currency": "USD"
                    }
                ),
                StateMutationMatch(
                    tablename="note",
                    action="INSERT",
                    values={
                        "data": "{}",
                        "post": SemanticMatchVariable(description="question asking if there are any updates"),
                        "type": "Post",
                        "deleted": False,
                        "is_global": False,
                        "is_pinned": False,
                        "parent_id": "3ac031b6dd8847cbb",
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
                # Opportunity 3: "Robust homogeneous groupware"
                StateMutationMatch(
                    tablename="opportunity",
                    action="UPDATE",
                    values={
                        "id": "8fd0e5081bbd4186a",
                        "name": "Robust homogeneous groupware",
                        "stage": "Qualification",
                        "amount": 438407.89,
                        "deleted": False,
                        "amount_currency": "USD"
                    }
                ),
                StateMutationMatch(
                    tablename="note",
                    action="INSERT",
                    values={
                        "data": "{}",
                        "post": SemanticMatchVariable(description="question asking if there are any updates"),
                        "type": "Post",
                        "deleted": False,
                        "is_global": False,
                        "is_pinned": False,
                        "parent_id": "8fd0e5081bbd4186a",
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
                # Opportunity 4: "Grass-roots reciprocal archive"
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
                ),
                StateMutationMatch(
                    tablename="note",
                    action="INSERT",
                    values={
                        "data": "{}",
                        "post": SemanticMatchVariable(description="question asking if there are any updates"),
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
                # Opportunity 5: "Centralized eco-centric emulation"
                StateMutationMatch(
                    tablename="opportunity",
                    action="UPDATE",
                    values={
                        "id": "5dbc1ba645304b5a9",
                        "name": "Centralized eco-centric emulation",
                        "stage": "Qualification",
                        "amount": 424414.53,
                        "deleted": False,
                        "amount_currency": "USD"
                    }
                ),
                StateMutationMatch(
                    tablename="note",
                    action="INSERT",
                    values={
                        "data": "{}",
                        "post": SemanticMatchVariable(description="question asking if there are any updates"),
                        "type": "Post",
                        "deleted": False,
                        "is_global": False,
                        "is_pinned": False,
                        "parent_id": "5dbc1ba645304b5a9",
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
                # Opportunity 6: "Compatible discrete infrastructure"
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
                        "post": SemanticMatchVariable(description="question asking if there are any updates"),
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
                # Opportunity 7: "Quality-focused directional database"
                StateMutationMatch(
                    tablename="opportunity",
                    action="UPDATE",
                    values={
                        "id": "11be4a8d2dbb4cc7a",
                        "name": "Quality-focused directional database",
                        "stage": "Qualification",
                        "amount": 405848.5,
                        "deleted": False,
                        "amount_currency": "USD"
                    }
                ),
                StateMutationMatch(
                    tablename="note",
                    action="INSERT",
                    values={
                        "data": "{}",
                        "post": SemanticMatchVariable(description="question asking if there are any updates"),
                        "type": "Post",
                        "deleted": False,
                        "is_global": False,
                        "is_pinned": False,
                        "parent_id": "11be4a8d2dbb4cc7a",
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

    # Add a task for all Accounts in Singapore to request updated financial statements for the new fiscal year
    PlatoTask(
      name="request_financial_statements_singapore",
      prompt="Add a task for all accounts located in Singapore to request updated financial statements for the new fiscal year. Set the due date to May 4th, 2025",
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
                tablename="task",
                action="INSERT",
                values={
                    "id": MutationVariable(name="task_id_1"),
                    "name": SemanticMatchVariable(description="somehing like request or update financial statements"),
                    "status": "Not Started",
                    "deleted": False,
                    "date_end": "2025-05-05T07:00:00",
                    "priority": "Normal",
                    "parent_id": "cdfa988475394882a",
                    "account_id": "cdfa988475394882a",
                    "parent_type": "Account",
                    "created_by_id": "680b027de457da0c5",
                    "date_end_date": "2025-05-04",
                    "assigned_user_id": "680b027de457da0c5",
                    "description": SemanticMatchVariable(description="something like update financial statements")
                }
            ),
            StateMutationMatch(
                tablename="note",
                action="INSERT",
                values={
                    "id": MutationVariable(name="note_id_1"),
                    "data": "{\"assignedUserId\":\"680b027de457da0c5\",\"assignedUserName\":\"Admin\",\"statusValue\":\"Not Started\",\"statusField\":\"status\",\"statusStyle\":\"default\"}",
                    "type": "Create",
                    "deleted": False,
                    "is_global": False,
                    "is_pinned": False,
                    "parent_id": MutationVariable(name="task_id_1"),
                    "related_id": None,
                    "is_internal": False,
                    "parent_type": "Task",
                    "target_type": None,
                    "related_type": None,
                    "created_by_id": "680b027de457da0c5",
                    "modified_by_id": None,
                    "super_parent_id": "cdfa988475394882a",
                    "super_parent_type": "Account"
                }
            ),
            StateMutationMatch(
                tablename="note_user",
                action="INSERT",
                values={
                    "deleted": False,
                    "note_id": MutationVariable(name="note_id_1"),
                    "user_id": "680b027de457da0c5"
                }
            ),
            StateMutationMatch(
                tablename="account",
                action="UPDATE",
                values={
                    "id": "cdfa988475394882a",
                    "name": "Wagner and Sons",
                    "type": "Partner",
                    "deleted": False,
                    "website": "http://graham-escobar.net/",
                    "industry": "Education",
                    "sic_code": None,
                    "campaign_id": None,
                    "description": "With anything morning cover name. Down trade significant step just notice serious. Indeed foot trade expert.",
                    "created_by_id": "93a49f0db93242168",
                    "modified_by_id": None,
                    "assigned_user_id": "023b7ca03adc49f99",
                    "billing_address_city": "Sellersport",
                    "billing_address_state": "Maryland",
                    "shipping_address_city": None,
                    "billing_address_street": "758 Lynn Turnpike Suite 690",
                    "shipping_address_state": None,
                    "billing_address_country": "Singapore",
                    "shipping_address_street": None,
                    "shipping_address_country": None,
                    "billing_address_postal_code": "98446",
                    "shipping_address_postal_code": None
                }
            ),
            StateMutationMatch(
                tablename="task",
                action="INSERT",
                values={
                    "id": MutationVariable(name="task_id_2"),
                    "name": SemanticMatchVariable(description="somehing like request or update financial statements"),
                    "status": "Not Started",
                    "deleted": False,
                    "date_end": "2025-05-05T07:00:00",
                    "priority": "Normal",
                    "parent_id": "ed05672c90aa47c0b",
                    "account_id": "ed05672c90aa47c0b",
                    "parent_type": "Account",
                    "created_by_id": "680b027de457da0c5",
                    "date_end_date": "2025-05-04",
                    "assigned_user_id": "680b027de457da0c5",
                    "description": SemanticMatchVariable(description="something like update financial statements")
                }
            ),
            StateMutationMatch(
                tablename="note",
                action="INSERT",
                values={
                    "id": MutationVariable(name="note_id_2"),
                    "data": "{\"assignedUserId\":\"680b027de457da0c5\",\"assignedUserName\":\"Admin\",\"statusValue\":\"Not Started\",\"statusField\":\"status\",\"statusStyle\":\"default\"}",
                    "type": "Create",
                    "deleted": False,
                    "is_global": False,
                    "is_pinned": False,
                    "parent_id": MutationVariable(name="task_id_2"),
                    "related_id": None,
                    "is_internal": False,
                    "parent_type": "Task",
                    "target_type": None,
                    "related_type": None,
                    "created_by_id": "680b027de457da0c5",
                    "modified_by_id": None,
                    "super_parent_id": "ed05672c90aa47c0b",
                    "super_parent_type": "Account"
                }
            ),
            StateMutationMatch(
                tablename="note_user",
                action="INSERT",
                values={
                    "deleted": False,
                    "note_id": MutationVariable(name="note_id_2"),
                    "user_id": "680b027de457da0c5"
                }
            ),
            StateMutationMatch(
                tablename="account",
                action="UPDATE",
                values={
                    "id": "ed05672c90aa47c0b",
                    "name": "Wilson-Olson",
                    "type": "Investor",
                    "deleted": False,
                    "website": "http://acevedo-mcdaniel.biz/",
                    "industry": "Healthcare",
                    "sic_code": None,
                    "campaign_id": None,
                    "description": "Billion certainly teacher prevent. Soldier local civil whatever. Table behind certain data price center. Over smile system program player.",
                    "created_by_id": "f69beb4defc149fd9",
                    "modified_by_id": None,
                    "assigned_user_id": "ba1345ba10c14590b",
                    "billing_address_city": "Port Alexton",
                    "billing_address_state": "Arizona",
                    "shipping_address_city": None,
                    "billing_address_street": "98462 Vargas Stream Apt. 685",
                    "shipping_address_state": None,
                    "billing_address_country": "Singapore",
                    "shipping_address_street": None,
                    "shipping_address_country": None,
                    "billing_address_postal_code": "63197",
                    "shipping_address_postal_code": None
                }
            )
        ]
      ),
    ),


]


all_tasks = (
    opportunities_tasks + contacts_and_accounts_tasks + leads_tasks + meetings_tasks + settings_tasks + multi_step_tasks
)
