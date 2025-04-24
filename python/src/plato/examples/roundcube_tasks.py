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


# 📧 compose emails
# compose email: to {recipient} with subject {subject} and formatted content including {elements}
# compose email: to {recipient} with attachment {file} and {formatting_elements}

compose_email_tasks = [
    PlatoTask(
        name="compose_project_proposal_email",
        prompt="Compose an HTML-formatted project proposal email to Jennifer Martinez, the Marketing Director at TechSolutions Inc. - Create a new email with bold section headers, bullet points for deliverables, a table showing the proposed timeline, and attach the full PDF proposal with a personalized message requesting feedback by Friday.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "An HTML-formatted project proposal email should be composed to Jennifer Martinez at TechSolutions Inc. with bold section headers, bullet points for deliverables, a timeline table, and a PDF proposal attachment with a request for feedback by Friday."),
        )
    ),
    PlatoTask(
        name="compose_job_application_email",
        prompt="Compose a detailed job application email to HR Manager Robert Johnson at Innovate Technologies - Create a message applying for the Senior Developer position, highlight your 7 years of relevant experience in bullet points, explain your specific interest in their AI projects, and attach your resume and code portfolio.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A detailed job application email should be composed to HR Manager Robert Johnson at Innovate Technologies, applying for the Senior Developer position, highlighting 7 years of experience in bullet points, explaining interest in AI projects, and attaching resume and code portfolio."),
        )
    ),
    PlatoTask(
        name="compose_conference_followup_email",
        prompt="Compose a follow-up email to Dr. Sarah Johnson regarding the medical conference presentation - Create a message thanking her for the opportunity to present, attach the revised slides incorporating her feedback, and request a 15-minute call next Tuesday to discuss the final logistics.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A follow-up email should be composed to Dr. Sarah Johnson regarding the medical conference presentation, thanking her for the opportunity, attaching revised slides with her feedback incorporated, and requesting a 15-minute call next Tuesday for logistics discussion."),
        )
    ),
    PlatoTask(
        name="compose_networking_followup_email",
        prompt="Compose a networking follow-up email to Richard Martinez whom you met at the industry conference - Thank him for the insightful conversation about renewable energy trends, reference the specific article he mentioned about solar efficiency, attach the research paper you discussed, and suggest meeting for coffee next month when you're in Boston.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A networking follow-up email should be composed to Richard Martinez, thanking him for the conversation about renewable energy trends, referencing his article about solar efficiency, attaching the discussed research paper, and suggesting a coffee meeting in Boston next month."),
        )
    ),
    PlatoTask(
        name="compose_event_invitation_email",
        prompt="Compose a detailed event invitation email to keynote speaker Dr. Emily Chen - Create a formal invitation to speak at your company's annual technology summit, specify the 45-minute time slot on October 15th, outline the audience demographics and expected attendance of 300+ industry professionals, and offer a $2,000 honorarium plus travel expenses.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A detailed event invitation email should be composed to Dr. Emily Chen, formally inviting her to speak at the annual technology summit for 45 minutes on October 15th, outlining audience demographics of 300+ professionals, and offering $2,000 honorarium plus travel expenses."),
        )
    ),
    PlatoTask(
        name="compose_sales_proposal_email",
        prompt="Compose a sales proposal email to potential client Maria Rodriguez at Global Retail Inc. - Create a personalized pitch highlighting how your inventory management solution addresses the specific challenges she mentioned in your meeting, include pricing options in a clear table format, and suggest three possible implementation timelines.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A sales proposal email should be composed to Maria Rodriguez at Global Retail Inc., with a personalized pitch about how the inventory management solution addresses her challenges, pricing options in a table format, and three possible implementation timelines."),
        )
    ),
    PlatoTask(
        name="compose_interview_scheduling_email",
        prompt="Compose a detailed interview scheduling email to software engineer candidate Rajesh Patel - Offer three specific time slots for the technical interview next week, explain the 90-minute format including the coding assessment portion, provide the names and roles of the four panel members, and ask about any accommodations he might need.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A detailed interview scheduling email should be composed to software engineer candidate Rajesh Patel, offering three time slots for next week, explaining the 90-minute format with coding assessment, providing names and roles of four panel members, and asking about needed accommodations."),
        )
    ),
    PlatoTask(
        name="compose_partnership_proposal_email",
        prompt="Compose a detailed partnership proposal email to Marketing Director Jason Kim at complementary business - Suggest a co-branded webinar series on industry trends, outline the specific benefits for both companies, propose a revenue-sharing model for generated leads, and request a meeting next week to discuss potential topics.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A detailed partnership proposal email should be composed to Marketing Director Jason Kim, suggesting a co-branded webinar series on industry trends, outlining benefits for both companies, proposing a revenue-sharing model for leads, and requesting a meeting next week to discuss topics."),
        )
    ),
    PlatoTask(
        name="compose_welcome_email",
        prompt="Compose a detailed welcome email to new team member Jessica Martinez - Create her first-day instructions including the 9:30 AM orientation location, attach required HR forms, provide login credentials for the company portal, list the team members she'll be meeting, and include the agenda for the department lunch.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A detailed welcome email should be composed to new team member Jessica Martinez with first-day instructions including 9:30 AM orientation location, attached HR forms, login credentials, team member list, and department lunch agenda."),
        )
    ),
    PlatoTask(
        name="compose_feedback_email",
        prompt="Compose a detailed feedback email to freelance designer Laura Johnson about logo concepts - Thank her for the initial designs, provide specific comments on each of the four options, request color variations for concept #2, explain the concerns about font readability in the third option, and confirm the revision deadline for next Tuesday.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A detailed feedback email should be composed to freelance designer Laura Johnson about logo concepts, thanking her for initial designs, providing comments on all four options, requesting color variations for concept #2, explaining font readability concerns, and confirming Tuesday revision deadline."),
        )
    ),
    PlatoTask(
        name="compose_recommendation_email",
        prompt="Compose a detailed recommendation email for former employee David Chen to hiring manager at partner company - Create a personalized reference highlighting his specific achievements on the database migration project, detail his leadership skills with examples, explain why he would be an excellent fit for their Data Architect role, and offer to discuss further by phone.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A detailed recommendation email should be composed for former employee David Chen to a hiring manager, highlighting his achievements on the database migration project, detailing leadership skills with examples, explaining his fit for the Data Architect role, and offering further phone discussion."),
        )
    ),
    PlatoTask(
        name="compose_project_kickoff_email",
        prompt="Compose a detailed project kickoff email to client team at Global Finance Corp - Create a comprehensive message to the five stakeholders, outline the project phases with specific deliverable dates, attach the requirements document for their review, assign initial action items to specific team members, and schedule the kickoff call for Monday at 2 PM.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A detailed project kickoff email should be composed to the client team at Global Finance Corp, addressing five stakeholders, outlining project phases with deliverable dates, attaching requirements document, assigning initial action items, and scheduling Monday 2 PM kickoff call."),
        )
    ),
    PlatoTask(
        name="compose_university_inquiry_email",
        prompt="Draft an email to University Admissions Director Patricia Garcia requesting information about the MBA program - Compose a formal inquiry introducing yourself as a prospective student, list your three specific questions about the international business concentration, mention your relevant work experience, and request information about scholarship opportunities.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A formal email should be drafted to University Admissions Director Patricia Garcia, introducing yourself as a prospective MBA student, listing three questions about international business concentration, mentioning relevant work experience, and requesting scholarship information."),
        )
    )
]


# 📩 reply to emails
# reply to email: from {sender} about {subject} with {content_elements}
# reply to all: on thread from {sender} with {content_elements}

reply_email_tasks = [
    PlatoTask(
        name="reply_to_budget_inquiry",
        prompt="Reply to David Wilson's quarterly budget inquiry with formatted financial data - Respond to the CFO's specific questions about Q3 marketing expenses by inserting an Excel table showing the breakdown of costs, highlight areas that were under budget in green, and explain the 12% overage in the digital advertising category.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A reply should be sent to David Wilson's quarterly budget inquiry with an Excel table showing Q3 marketing expense breakdown, highlighting under-budget areas in green, and explaining the 12% overage in digital advertising."),
        )
    ),
    PlatoTask(
        name="reply_to_board_meeting",
        prompt="Reply to all participants of yesterday's board meeting with action items and meeting minutes - Respond to the thread from CEO Thomas Williams, format each assigned task with the responsible person's name in bold, include the decision points in a numbered list, and attach the complete minutes document.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A reply-all should be sent to yesterday's board meeting participants, responding to CEO Thomas Williams' thread, formatting assigned tasks with responsible persons' names in bold, including decision points in a numbered list, and attaching complete minutes."),
        )
    ),
    PlatoTask(
        name="reply_to_customer_complaint",
        prompt="Reply to customer complaint from Elizabeth Brown about the defective product shipment - Respond with a sincere apology, explain the specific steps you're taking to resolve the issue, offer a 30% discount on her next order, and request her shipping address to send a replacement immediately.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A reply should be sent to Elizabeth Brown's customer complaint about the defective product shipment, with a sincere apology, explanation of resolution steps, offer of 30% discount on next order, and request for shipping address for immediate replacement."),
        )
    ),
    PlatoTask(
        name="reply_to_research_proposal_feedback",
        prompt="Reply to Professor Williams' feedback on your research proposal with specific revisions - Address each of her comments about your methodology section, explain the changes you've made to the statistical analysis approach, attach the revised document with tracked changes, and ask about extending the data collection period.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A reply should be sent to Professor Williams' feedback on the research proposal, addressing her methodology comments, explaining statistical analysis changes, attaching revised document with tracked changes, and asking about extending data collection period."),
        )
    ),
    PlatoTask(
        name="reply_to_team_member_questions",
        prompt="Reply to team member Alex Johnson's questions about the new project management software - Address his specific concerns about the learning curve, provide step-by-step instructions with screenshots for setting up his dashboard, and offer to schedule a 30-minute training session on Thursday morning.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A reply should be sent to team member Alex Johnson's questions about the new project management software, addressing learning curve concerns, providing dashboard setup instructions with screenshots, and offering a 30-minute Thursday morning training session."),
        )
    ),
    PlatoTask(
        name="reply_to_website_revision_requests",
        prompt="Reply to client Emma Wilson's website revision requests with clarifying questions - Acknowledge her feedback on the homepage design, ask specific questions about the preferred color scheme changes, include two alternative navigation layouts as screenshots, and confirm if the requested changes should apply to the mobile version as well.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A reply should be sent to client Emma Wilson's website revision requests, acknowledging homepage design feedback, asking about preferred color scheme changes, including two alternative navigation layout screenshots, and confirming if changes apply to mobile version."),
        )
    ),
    PlatoTask(
        name="reply_to_service_outage",
        prompt="Compose a detailed apology email to customer Thomas Garcia for the service outage - Explain the specific cause of yesterday's 3-hour platform downtime, detail the steps taken to prevent recurrence, offer a 50% discount on next month's subscription, and provide direct contact information for the support manager.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A detailed apology email should be composed to customer Thomas Garcia about the service outage, explaining the cause of the 3-hour platform downtime, detailing prevention steps, offering 50% discount on next month's subscription, and providing support manager contact information."),
        )
    ),
    PlatoTask(
        name="reply_to_delivery_delay",
        prompt="Reply to vendor Daniel Wilson about delivery delay with alternative solutions - Address the notification about the 3-week shipping delay for office furniture, request expedited delivery for essential items, ask about partial substitutions from in-stock inventory, and inquire about compensation options for the inconvenience.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A reply should be sent to vendor Daniel Wilson about the delivery delay, addressing the 3-week shipping delay for office furniture, requesting expedited delivery for essential items, asking about partial substitutions from in-stock inventory, and inquiring about compensation options."),
        )
    ),
    PlatoTask(
        name="reply_to_conference_organizer",
        prompt="Reply to conference organizer Michael Smith with your presentation requirements - Confirm your acceptance as a speaker at the industry event, specify your technical needs including HDMI connection and wireless microphone, attach your speaker bio and high-resolution photo, and inquire about the Q&A format.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A reply should be sent to conference organizer Michael Smith with presentation requirements, confirming speaker acceptance, specifying technical needs (HDMI connection and wireless microphone), attaching speaker bio and high-resolution photo, and inquiring about Q&A format."),
        )
    ),
    PlatoTask(
        name="reply_to_investor_questions",
        prompt="Reply to investor Susan Chang's questions about quarterly financial results - Address her specific concerns about the 7% revenue decrease in the European market, provide additional context about the temporary regulatory impact, include a small chart showing the expected recovery timeline, and offer to discuss further on the upcoming investor call.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A reply should be sent to investor Susan Chang's questions about quarterly financial results, addressing concerns about 7% European market revenue decrease, providing context about temporary regulatory impact, including recovery timeline chart, and offering further discussion on upcoming investor call."),
        )
    ),
    PlatoTask(
        name="reply_to_journalist_interview_request",
        prompt="Reply to journalist Rebecca Martinez's interview request about your company's sustainability initiative - Respond to the reporter from Business Weekly, answer her specific questions about your carbon reduction goals, offer additional data points about your renewable energy transition, suggest the CEO as an additional interview subject, and propose times for a 30-minute call next week.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A reply should be sent to journalist Rebecca Martinez from Business Weekly about the sustainability initiative interview request, answering carbon reduction goal questions, offering renewable energy transition data, suggesting the CEO as additional interview subject, and proposing times for a 30-minute call next week."),
        )
    )
]


# 📤 forward emails
# forward email: from {sender} to {recipient} with {additional_content}
# forward email: from {sender} to {recipients} with {annotations} and cc {cc_recipients}

forward_email_tasks = [
    PlatoTask(
        name="forward_technical_specifications",
        prompt="Forward Michael Chen's technical specifications email to the engineering team with additional context - Take the detailed product requirements from the client, add your annotations in a different color above each section, highlight three critical deadlines, and CC the project manager with a note about prioritizing the API integration component.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "Michael Chen's technical specifications email should be forwarded to the engineering team with annotations in a different color above each section, three critical deadlines highlighted, and CC'd to the project manager with a note about prioritizing API integration."),
        )
    ),
    PlatoTask(
        name="forward_legal_contract",
        prompt="Forward legal contract from attorney Michelle Park to business partner with your annotations - Share the partnership agreement draft, highlight three concerning clauses about intellectual property ownership, add your comments about suggested revisions to the payment terms, and request a call tomorrow to align on negotiation strategy.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The legal contract from attorney Michelle Park should be forwarded to the business partner, highlighting three concerning IP ownership clauses, adding comments about payment term revisions, and requesting a call tomorrow about negotiation strategy."),
        )
    ),
    PlatoTask(
        name="forward_customer_testimonial",
        prompt="Forward customer testimonial from Sarah Williams to the marketing team with usage instructions - Share the enthusiastic feedback email, highlight the key quotes about product reliability, suggest using it in the upcoming case study, and request permission from the customer before publishing on the website.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The customer testimonial from Sarah Williams should be forwarded to the marketing team, highlighting key product reliability quotes, suggesting use in upcoming case study, and requesting customer permission before website publication."),
        )
    ),
    PlatoTask(
        name="forward_vendor_quote",
        prompt="Forward vendor quote from Samantha Lee to your purchasing department with approval request - Send the detailed pricing proposal from Office Solutions Inc. to Procurement Director Mark Thompson, highlight the 15% volume discount in the third section, and add your recommendation to proceed with the annual contract option.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The vendor quote from Samantha Lee at Office Solutions Inc. should be forwarded to Procurement Director Mark Thompson, highlighting the 15% volume discount in the third section, with a recommendation to proceed with the annual contract option."),
        )
    ),
    PlatoTask(
        name="forward_security_alert",
        prompt="Forward urgent security alert from IT Director to all department heads with additional instructions - Share the notification about the phishing attempt, add your specific guidelines for staff to verify sender addresses, bold the warning about password requests, and request confirmation that each department has briefed their teams by end of day.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The urgent security alert from IT Director should be forwarded to all department heads, adding specific guidelines for verifying sender addresses, bolding the password request warning, and requesting confirmation of team briefings by end of day."),
        )
    )
]


# 👤 contact management
# add contact: {contact_name} with details {contact_details} and add to groups {groups}
# update contact: {contact_name} with new {field} {value}
# create contact group: {group_name} with {properties}
# import/export contacts: {action} {source/destination} with {options}

contact_management_tasks = [
    PlatoTask(
        name="add_medical_professional_contact",
        prompt="Add Dr. Samantha Rodriguez to contacts with her professional details - Create a new contact for the Chief Medical Officer at Memorial Hospital, including her email address samantha.rodriguez@memorialhospital.org, office phone number +1-415-555-7890, and mobile number +1-415-555-1234. Add her to both the \"Healthcare Partners\" and \"VIP Contacts\" groups, and include a note about her preference for morning communications.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A new contact should be created for Dr. Samantha Rodriguez, Chief Medical Officer at Memorial Hospital, with email samantha.rodriguez@memorialhospital.org, office phone +1-415-555-7890, mobile +1-415-555-1234, added to \"Healthcare Partners\" and \"VIP Contacts\" groups, with a note about morning communication preference."),
        )
    ),
    PlatoTask(
        name="create_project_team_contact_group",
        prompt="Create a \"Project Phoenix Team\" contact group for the cross-departmental initiative - Set up a new contact group specifically for the 12 team members working on the Project Phoenix software migration. Include members from IT, Operations, and Finance departments, with appropriate color-coding to distinguish department representatives at a glance during email composition.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A new contact group named \"Project Phoenix Team\" should be created for the 12 team members working on the software migration, including members from IT, Operations, and Finance departments, with color-coding to distinguish department representatives during email composition."),
        )
    ),
    PlatoTask(
        name="update_contact_with_promotion",
        prompt="Update James Wilson's contact information with his new position and contact details - Modify the existing contact for James Wilson to reflect his promotion to Senior Product Manager, update his email from james.wilson@technova.io to james.wilson@technova-executive.io, add his new direct line +1-415-555-8901, and move him from the \"Product Team\" group to both \"Leadership Team\" and \"Product Strategy Committee\" groups.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "James Wilson's contact should be updated to reflect his promotion to Senior Product Manager, with email changed from james.wilson@technova.io to james.wilson@technova-executive.io, new direct line +1-415-555-8901 added, and moved from \"Product Team\" group to \"Leadership Team\" and \"Product Strategy Committee\" groups."),
        )
    ),
    PlatoTask(
        name="import_vendor_contacts",
        prompt="Import the quarterly updated vendor contact list from the procurement CSV file - Access the vendor_contacts_q2_2025.csv file from the Procurement department, import all 47 contacts while ensuring existing contacts are updated rather than duplicated, map the \"Vendor Category\" field to appropriate contact groups, and verify all phone numbers are formatted with the international code.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The vendor_contacts_q2_2025.csv file should be imported with all 47 contacts, updating existing contacts rather than duplicating them, mapping the \"Vendor Category\" field to appropriate contact groups, and verifying phone numbers are formatted with international code."),
        )
    ),
    PlatoTask(
        name="merge_duplicate_contacts",
        prompt="Merge duplicate entries for Elizabeth Chen across personal and work address books - Identify and combine the three separate contact entries for Elizabeth Chen (elizabeth.chen@gmail.com, liz.chen@partner.org, and beth.chen@technova.io) into a single comprehensive contact with separate work, personal, and partner organization email fields, consolidating all phone numbers, addresses, and group memberships.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The three separate contact entries for Elizabeth Chen (elizabeth.chen@gmail.com, liz.chen@partner.org, and beth.chen@technova.io) should be merged into a single comprehensive contact with separate email fields, consolidating all phone numbers, addresses, and group memberships."),
        )
    ),
    PlatoTask(
        name="add_profile_picture_to_contact",
        prompt="Add profile picture to Michael Johnson's contact from the team directory photo - Update the existing contact for the new UX Designer by adding his professional headshot from the company directory, resize the image to fit the contact card properly, ensure it displays correctly in both the contacts list and when composing emails to him.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "Michael Johnson's contact should be updated by adding his professional headshot from the company directory, resized to fit the contact card properly, ensuring it displays correctly in both the contacts list and when composing emails."),
        )
    ),
    PlatoTask(
        name="create_detailed_client_contact",
        prompt="Create detailed contact entry for new client representative Victoria Blackwell with full company information - Add a new contact for the Director of Operations at Meridian Systems, including her email victoria.blackwell@meridiansystems.com, office phone +1-628-555-4321, company address with suite number, assistant's contact information (Emma Parker, emma.parker@meridiansystems.com), and add her to both \"Active Clients\" and \"Quarterly Review Participants\" groups.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A detailed contact entry should be created for Victoria Blackwell, Director of Operations at Meridian Systems, with email victoria.blackwell@meridiansystems.com, office phone +1-628-555-4321, company address with suite number, assistant's contact information, and added to \"Active Clients\" and \"Quarterly Review Participants\" groups."),
        )
    ),
    PlatoTask(
        name="export_conference_attendees",
        prompt="Export the \"Conference Attendees\" contact group to share with the event planning team - Select the specific contact group containing all 28 registered attendees for the upcoming industry conference, export to a CSV file with fields for name, email, company, dietary preferences, and session tracks, then save to the shared Events folder for access by the logistics team.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The \"Conference Attendees\" contact group with 28 registered attendees should be exported to a CSV file with fields for name, email, company, dietary preferences, and session tracks, saved to the shared Events folder for the logistics team."),
        )
    ),
    PlatoTask(
        name="organize_engineering_contacts",
        prompt="Organize the Engineering department contacts into specialized sub-groups - Create three new contact sub-groups under the main \"Engineering\" group: \"Frontend Developers\" (8 contacts), \"Backend Developers\" (12 contacts), and \"QA Engineers\" (6 contacts), then properly categorize each existing engineering contact into the appropriate sub-group while maintaining their presence in the main group.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "Three new contact sub-groups should be created under the main \"Engineering\" group: \"Frontend Developers\" (8 contacts), \"Backend Developers\" (12 contacts), and \"QA Engineers\" (6 contacts), with each engineering contact properly categorized while maintaining presence in the main group."),
        )
    ),
    PlatoTask(
        name="add_hr_replacement_contact",
        prompt="Add detailed contact information for Sarah Chen's replacement at TechNova - Create a new contact for Rebecca Martinez who is taking over as Head of HR, including her email rebecca.martinez@technova.io, direct line +1-415-555-0199, mobile +1-415-555-0200, office location (Building B, Floor 4, Office 422), and add her to the \"Leadership Team,\" \"HR Team,\" and \"Compensation Review Committee\" groups.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A new contact should be created for Rebecca Martinez, the new Head of HR replacing Sarah Chen, with email rebecca.martinez@technova.io, direct line +1-415-555-0199, mobile +1-415-555-0200, office location details, and added to \"Leadership Team,\" \"HR Team,\" and \"Compensation Review Committee\" groups."),
        )
    ),
    PlatoTask(
        name="remove_defunct_vendor_contacts",
        prompt="Search for and remove all contacts from the defunct Westside Partners vendor - Perform a search for all contacts containing \"westside\" or \"westsidepartners.com\" email domains, identify the 5 contacts from this vendor that is no longer in business, remove them from all contact groups, and permanently delete them from the address book.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "All contacts containing \"westside\" or \"westsidepartners.com\" email domains should be searched for, the 5 contacts from this defunct vendor identified, removed from all contact groups, and permanently deleted from the address book."),
        )
    ),
    PlatoTask(
        name="create_vip_speaker_contact",
        prompt="Create a VIP contact entry for keynote speaker Dr. James Peterson with presentation details - Add a new contact for the AI Ethics expert speaking at your upcoming company event, including his academic email james.peterson@stanford.edu, personal email drjp@gmail.com, assistant's contact (Mary Williams, mary.williams@stanford.edu), special note about his presentation requirements, and add him to both \"Event Speakers\" and \"External Experts\" groups.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A VIP contact entry should be created for keynote speaker Dr. James Peterson, including academic email james.peterson@stanford.edu, personal email drjp@gmail.com, assistant's contact information, presentation requirements note, and added to \"Event Speakers\" and \"External Experts\" groups."),
        )
    ),
    PlatoTask(
        name="bulk_update_marketing_emails",
        prompt="Update the entire Marketing Team contact group with new department prefix in email addresses - Select all 17 contacts in the \"Marketing Team\" group and bulk edit their email addresses to change the format from firstname.lastname@technova.io to firstname.lastname@mkt.technova.io, ensuring all group memberships and other contact details remain intact after the update.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "All 17 contacts in the \"Marketing Team\" group should have their email addresses bulk edited from firstname.lastname@technova.io to firstname.lastname@mkt.technova.io, with all group memberships and other contact details remaining intact."),
        )
    ),
    PlatoTask(
        name="add_networking_contact",
        prompt="Add Ryan Henderson's complete contact details after yesterday's networking event - Create a new contact based on the business card received from the Senior Software Engineer at CloudMatrix, including his work email ryan.henderson@cloudmatrix.com, personal email ryan.h.1982@gmail.com, mobile number +1-415-555-6789, LinkedIn profile URL, note about his interest in your AI project, and add him to the \"Industry Connections\" and \"Potential Recruits\" groups.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A new contact should be created for Ryan Henderson, Senior Software Engineer at CloudMatrix, with work email ryan.henderson@cloudmatrix.com, personal email ryan.h.1982@gmail.com, mobile +1-415-555-6789, LinkedIn URL, note about AI project interest, and added to \"Industry Connections\" and \"Potential Recruits\" groups."),
        )
    ),
    PlatoTask(
        name="create_client_contact_with_account_info",
        prompt="Create a detailed contact entry for new client Olivia Taylor with account-specific information - Add a new contact for the Project Manager at GreenTech Solutions, including her email olivia.taylor@greentechsolutions.com, office phone +1-415-555-3456, mobile +1-415-555-7890, company address, contract number GT-2025-0734, billing contact information (finance@greentechsolutions.com), and add her to the \"Active Clients\" and \"Sustainability Initiative\" groups.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A detailed contact entry should be created for Olivia Taylor, Project Manager at GreenTech Solutions, with email olivia.taylor@greentechsolutions.com, office and mobile phones, company address, contract number GT-2025-0734, billing contact information, and added to \"Active Clients\" and \"Sustainability Initiative\" groups."),
        )
    )
]


# 📁 folder & organization tasks
# create folder: {folder_name} with {properties}
# set up filter: for {criteria} to {action}
# organize emails: in {folder} using {organization_method}

folder_organization_tasks = [
    PlatoTask(
        name="create_project_folder_structure",
        prompt="Create a hierarchical project folder structure for the Anderson account - Create a new parent folder called \"Anderson Corp 2025 Redesign\" with four nested subfolders: \"Requirements Documentation,\" \"Weekly Status Reports,\" \"Client Feedback,\" and \"Invoice Records.\" Set custom icons for each subfolder and apply a blue color tag to the parent folder for easy identification.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A hierarchical project folder structure should be created with a parent folder \"Anderson Corp 2025 Redesign\" containing four nested subfolders (\"Requirements Documentation,\" \"Weekly Status Reports,\" \"Client Feedback,\" and \"Invoice Records\"), with custom icons for each subfolder and a blue color tag for the parent folder."),
        )
    ),
    PlatoTask(
        name="rename_department_folder",
        prompt="Rename the outdated \"Legacy Systems\" folder to reflect the new department name - Change the folder previously used for the IT Legacy Systems team to \"Infrastructure Modernization Team,\" maintaining all existing filter rules and folder permissions. Update the associated color tag from red to the new department's purple branding.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The \"Legacy Systems\" folder should be renamed to \"Infrastructure Modernization Team,\" maintaining all existing filter rules and folder permissions, with the color tag updated from red to purple."),
        )
    ),
    PlatoTask(
        name="purge_old_trash_items",
        prompt="Permanently purge all items from the Trash folder older than 90 days - Access the Trash folder containing 1,247 deleted items, sort by date, select all messages from before January 15, 2025, and permanently delete them to free up 2.3GB of storage space. Confirm the permanent deletion and document the space recovered for the quarterly IT audit.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "All items in the Trash folder older than 90 days (before January 15, 2025) should be permanently deleted, freeing up 2.3GB of storage space, with the deletion confirmed and space recovered documented for the quarterly IT audit."),
        )
    ),
    PlatoTask(
        name="create_advanced_search_query",
        prompt="Create a comprehensive search query for all project documentation from the Martinez lawsuit - Construct an advanced search query to find all emails containing \"Martinez,\" \"case #2024-CV-7823,\" \"settlement,\" or \"deposition\" from between March 15-June 30, 2024, excluding automated notifications, and save this search as \"Martinez Case Documentation\" for future reference.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "An advanced search query should be created to find all emails containing \"Martinez,\" \"case #2024-CV-7823,\" \"settlement,\" or \"deposition\" from March 15-June 30, 2024, excluding automated notifications, and saved as \"Martinez Case Documentation.\""),
        )
    ),
    PlatoTask(
        name="set_up_competitor_intelligence_filter",
        prompt="Set up a multi-condition filter for competitor intelligence emails - Create a sophisticated filter that identifies messages from industry newsletters (using domains techweekly.com, industryinsider.org, and competitorwatch.net) containing keywords \"market share,\" \"new product,\" or \"strategic partnership\" related to your top three competitors, and automatically move these to a dedicated \"Competitor Intelligence\" folder with high-priority flagging.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A multi-condition filter should be set up to identify messages from industry newsletters (techweekly.com, industryinsider.org, competitorwatch.net) containing keywords related to competitors, automatically moving them to a \"Competitor Intelligence\" folder with high-priority flagging."),
        )
    ),
    PlatoTask(
        name="reorganize_financial_reports",
        prompt="Reorganize the quarterly financial reports using a date-based folder structure - Create a new hierarchical system for storing financial reports with a parent \"Finance\" folder containing year subfolders (2023, 2024, 2025), each with quarter subfolders (Q1, Q2, Q3, Q4), then move all 48 existing financial report emails to their appropriate locations based on their received dates.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A hierarchical system should be created for financial reports with a parent \"Finance\" folder containing year subfolders (2023, 2024, 2025), each with quarter subfolders (Q1, Q2, Q3, Q4), with all 48 existing financial report emails moved to appropriate locations based on received dates."),
        )
    ),
    PlatoTask(
        name="apply_color_coding_system",
        prompt="Apply a graduated color-coding system to the product development email categories - Implement a visual organization system for the product development workflow by applying red tags to \"Critical Bugs\" emails, orange for \"Feature Requests,\" yellow for \"In Development,\" green for \"Ready for Testing,\" and blue for \"Deployed to Production,\" then update the 37 existing emails in these categories.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A graduated color-coding system should be applied to product development emails: red for \"Critical Bugs,\" orange for \"Feature Requests,\" yellow for \"In Development,\" green for \"Ready for Testing,\" and blue for \"Deployed to Production,\" with all 37 existing emails updated accordingly."),
        )
    ),
    PlatoTask(
        name="create_automated_filing_system",
        prompt="Create an automated filing system for monthly expense reports from the sales team - Set up a filter rule that detects incoming emails with subject lines containing \"Expense Report\" from any address ending with @salesteam.technova.io, extracts the month from the subject line (format: \"Expenses - [Month] 2025\"), and files it in a corresponding monthly subfolder within the \"Sales Expenses 2025\" directory.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "An automated filing system should be created for monthly expense reports, detecting emails with \"Expense Report\" in the subject from @salesteam.technova.io addresses, extracting the month from the subject, and filing in corresponding monthly subfolders within \"Sales Expenses 2025.\""),
        )
    ),
    PlatoTask(
        name="configure_out_of_office_response",
        prompt="Configure a comprehensive out-of-office auto-response for your two-week international business trip - Set up an automatic reply that activates from May 15-29, 2025, with different messages for internal colleagues (including your international phone number and hotel information) versus external contacts (providing alternative contact information for urgent matters). Include timezone information and specify limited email access periods.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A comprehensive out-of-office auto-response should be configured for May 15-29, 2025, with different messages for internal colleagues (including international phone and hotel information) versus external contacts (with alternative contact information), including timezone and limited email access details."),
        )
    ),
    PlatoTask(
        name="design_html_email_signature",
        prompt="Design a professional HTML email signature with dynamic content based on recipient - Create a signature containing your name, title, company logo, and contact information that displays different elements depending on the recipient's domain: showing your direct line to internal colleagues, displaying your cell phone to partners with domains in your approved list, and showing only office general contact information to others.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A professional HTML email signature should be designed with dynamic content based on recipient domain: showing direct line to internal colleagues, cell phone to approved partner domains, and only general office contact information to others."),
        )
    )
]


# ⚙️ settings & preferences tasks
# configure language: {language_settings} for {purpose}
# customize interface: {interface_elements} with {settings}
# set security: {security_features} with {parameters}

settings_preferences_tasks = [
    PlatoTask(
        name="configure_multilingual_settings",
        prompt="Configure the interface language settings for your multilingual team collaboration - Change your email client's display language to Spanish for your upcoming three-month project with the Madrid office, while maintaining English spell-checking for outgoing messages and setting up automatic translation for incoming messages from the Japanese team members.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The email client's display language should be changed to Spanish for the Madrid office project, while maintaining English spell-checking for outgoing messages and setting up automatic translation for incoming messages from Japanese team members."),
        )
    ),
    PlatoTask(
        name="synchronize_time_settings",
        prompt="Synchronize email client time settings with the Sydney office for the joint project - Adjust your email time zone settings from Pacific Time (UTC-7) to Australian Eastern Standard Time (UTC+10) for the duration of the six-week collaboration with the Sydney team, ensuring meeting invitations display in the correct time and email timestamps align with their business hours.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "Email time zone settings should be adjusted from Pacific Time (UTC-7) to Australian Eastern Standard Time (UTC+10) for the six-week Sydney team collaboration, ensuring meeting invitations and email timestamps align with their business hours."),
        )
    ),
    PlatoTask(
        name="customize_message_reading_workflow",
        prompt="Customize the message reading workflow for efficient email processing - Configure the email client to automatically mark messages as read after 3 seconds of viewing in the preview pane, enable the \"mark as read when selecting next message\" option, and set up keyboard shortcuts (Alt+R for Reply, Alt+F for Forward, Alt+D for Delete) to streamline your daily email processing routine.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The message reading workflow should be customized to automatically mark messages as read after 3 seconds in the preview pane, enable \"mark as read when selecting next message,\" and set up keyboard shortcuts (Alt+R for Reply, Alt+F for Forward, Alt+D for Delete)."),
        )
    ),
    PlatoTask(
        name="implement_visual_identity",
        prompt="Implement the company's new visual identity across your email interface - Apply the newly approved corporate visual identity by changing the interface theme to \"Dark Mode Professional,\" setting the accent color to the company's new Pantone 2935C blue, uploading the updated company logo for the header, and adjusting the font to the newly mandated Roboto for all interface elements.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The company's new visual identity should be implemented by changing the interface theme to \"Dark Mode Professional,\" setting the accent color to Pantone 2935C blue, uploading the updated company logo, and adjusting the font to Roboto for all interface elements."),
        )
    ),
    PlatoTask(
        name="optimize_inbox_display",
        prompt="Optimize the inbox display for high-volume email management - Increase the number of emails displayed per page from the default 50 to 150, enable the three-line preview for each message, add the \"attachment indicator\" and \"priority flag\" columns to the message list, and configure compact spacing to maximize the number of visible messages on your 27-inch monitor.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "The inbox display should be optimized by increasing emails per page from 50 to 150, enabling three-line message previews, adding \"attachment indicator\" and \"priority flag\" columns, and configuring compact spacing to maximize visible messages on a 27-inch monitor."),
        )
    ),
    PlatoTask(
        name="set_up_draft_autosaving",
        prompt="Set up a progressive draft auto-saving system based on message importance - Configure the email client to automatically save drafts of regular emails every 3 minutes, but increase frequency to every 30 seconds for messages containing the keywords \"urgent,\" \"proposal,\" or \"contract\" in the subject line, and enable local backup of drafts to prevent loss during server connectivity issues.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "A progressive draft auto-saving system should be configured to save regular email drafts every 3 minutes, increasing to every 30 seconds for messages with keywords \"urgent,\" \"proposal,\" or \"contract\" in the subject, with local backup enabled to prevent loss during connectivity issues."),
        )
    ),
    PlatoTask(
        name="standardize_html_formatting",
        prompt="Standardize the department's HTML email formatting for consistent corporate communications - Configure your default HTML message settings to use Arial 11pt for body text, Arial 14pt bold in corporate blue (#0052CC) for headings, set line spacing to 1.2, enable automatic bulleted lists, set default paragraph spacing to 8pt, and include the approved legal disclaimer text as an automatic footer for all outgoing messages.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "HTML email formatting should be standardized with Arial 11pt for body text, Arial 14pt bold in corporate blue (#0052CC) for headings, 1.2 line spacing, automatic bulleted lists, 8pt paragraph spacing, and the approved legal disclaimer as an automatic footer for all outgoing messages."),
        )
    ),
    PlatoTask(
        name="implement_encryption_for_legal",
        prompt="Implement end-to-end encryption for communications with the legal department - Set up PGP encryption for all email exchanges with addresses in the legal@technova.io domain, import the public keys for all 8 team members, configure automatic encryption for any outgoing messages to these recipients, and create a backup of your private key with password protection on the secure company server.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "End-to-end encryption should be implemented for communications with the legal department, setting up PGP encryption for the legal@technova.io domain, importing public keys for all 8 team members, configuring automatic encryption, and creating a password-protected backup of the private key."),
        )
    ),
    PlatoTask(
        name="update_account_security",
        prompt="Update your account security settings following the IT department's new requirements - Change your email account password to comply with the new 16-character minimum requirement with special characters, enable two-factor authentication using the company-approved authenticator app, set up account activity notifications for logins from new devices, and register your backup recovery phone number.",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "Account security settings should be updated to comply with IT requirements: changing password to meet 16-character minimum with special characters, enabling two-factor authentication with the approved app, setting up login notifications for new devices, and registering a backup recovery phone number."),
        )
    ),
    PlatoTask(
        name="optimize_email_retrieval",
        prompt="Optimize email retrieval settings for your hybrid work schedule - Configure your email client to check for new messages every 5 minutes while on the office network, reduce to every 15 minutes when connected via VPN from home, disable automatic checking when on mobile data connections, and set up push notifications only for messages from your manager and direct reports during business hours (8am-6pm).",
        start_url="http://roundcube.com",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "Email retrieval settings should be optimized for a hybrid work schedule: checking every 5 minutes on office network, every 15 minutes on VPN from home, disabling automatic checking on mobile data, and setting up push notifications only for messages from manager and direct reports during business hours."),
        )
    )
]


all_tasks = compose_email_tasks + reply_email_tasks + forward_email_tasks + contact_management_tasks + folder_organization_tasks + settings_preferences_tasks
