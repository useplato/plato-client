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


companies_tasks = [
    PlatoTask(
        name="create_new_company",
        prompt="Create a new company called 'Pearson Hardman' with a phone number of 785-940-4939, a fax of 839-483-4394, an email of info@pearsonhardman.com",
        env_id="snipeit",
      
    ),

    PlatoTask(
        name="update_company",
        prompt="Update the company 'Pearson Hardman' with a phone number of 987-654-3210, a fax of 123-456-7890, an email of info@pearsonhardman2.com",
        env_id="snipeit",
    ),

    PlatoTask(
        name="delete_company",
        prompt="Delete the company 'Pearson Hardman'",
        env_id="snipeit",
    ),
   
]

users_tasks = [
    PlatoTask(
        name="create_new_user",
        prompt="Create a new user called 'Bob McDonald' with a username of bobmcdonald234, a password of password (can login) an email of bobmcdonald@example.com",
        env_id="snipeit",
      
    ),

    PlatoTask(
        name="update_user",
        prompt="Update the user 'Bob McDonald' a new password of password2 (can login) an email of bobmcdonald@example.com",
        env_id="snipeit",
    ),    

    PlatoTask(
        name="update_user_permissions",
        prompt="Update the user 'Bob McDonald' to grant them admin and super user permissions, grant view, create and edit for accessories and deny delete for deparments",
        env_id="snipeit",
    ),

    PlatoTask(
        name="delete_user",
        prompt="Delete the user 'Bob McDonald'",
        env_id="snipeit",
    ),
    
    
]

manufacturers_tasks = [
    PlatoTask(
        name="create_manufacturer",
        prompt="Create a new manufacturer called 'Efficient Labour' with a url of https://www.efficientlabour.com, a warranty url of https://www.efficientlabour.com/warranty, a support phone of 123-456-7890, a support email of support@efficientlabour.com",
        env_id="snipeit",
    ),

    PlatoTask(
        name="update_manufacturer",
        prompt="Update the manufacturer 'Efficient Labour' to change the url to https://www.evenmorewaymoreefficientlabour.com, a warranty url of https://www.evenmorewaymoreefficientlabour.com/new/warranty222, a support phone of 999-456-7890, a support email of support@evenmorewaymoreefficientlabour.com",
        env_id="snipeit",
    ),

    PlatoTask(
        name="delete_manufacturer",
        prompt="Delete the manufacturer 'Efficient Labour'",
        env_id="snipeit",
    ),

]

assets_tasks = [

    PlatoTask(
        name="create_asset",
        prompt="Create a new asset called 'Crystal Lamp' for company Espinoza-Vasquez with a serial number of 1234, status of Ready to Deploy and a default location of Port Rachel and is requestable. It should bea new model of the name 'New Crystal Lamp' with category seat supplies and a manufacturer of Wright-Davis and a model number of 234567890, ",
        env_id="snipeit",
    ),
    
    PlatoTask(
        name="update_asset",
        prompt="Update the asset 'Crystal Lamp' to change the default location to New Joseph and a note of 'Awesome lamp!!!",
        env_id="snipeit",
    ),

    PlatoTask(
        name="checkout_asset", 
        prompt="Checkout the asset 'Crystal Lamp' to user Bob McDonald for 30 days from present date (expecteed checkin date) and change status to deployed",
        env_id="snipeit",
    ),

    PlatoTask(
        name="checkin_asset",
        prompt="Checkin the asset 'Crystal Lamp' to location Kiaratown and change status to Ready to Deploy",
        env_id="snipeit",
    ),
    
    PlatoTask(
        name="archive_asset",
        prompt="Archive the asset 'Crystal Lamp'",
        env_id="snipeit",
    ),
    
    PlatoTask(
        name="clone_asset",
        prompt="Clone the asset 'Crystal Lamp' to a new asset called 'Crystal Lamp Clone' with a serial number of 1234567890, a model number of 'New Crystal Lamp', a location of 'Kiaratown', a status of 'Ready to Deploy', a category of 'Laptop",
        env_id="snipeit",
    ),
    
    PlatoTask(
        name="delete_asset",
        prompt="Delete the asset 'Crystal Lamp'",
        env_id="snipeit",
    ),


    PlatoTask(
        name="bulk_checkout_assets",
        prompt="Bulk checkout all the assets for Music Max and Several Mini to user Franklin with a checkout date of 2024-01-01 and a expected checkin date of 2024-01-31",
        env_id="snipeit",
    ),

    PlatoTask(
        name="bulk_checkin_assets",
        prompt="Bulk checkin all the assets with asset tag 2353 with a status of Deployed and location of Kiaratown",
        env_id="snipeit",
    ),

]


all_tasks = (
    companies_tasks + users_tasks + manufacturers_tasks + assets_tasks
)
