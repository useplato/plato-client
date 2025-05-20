import json
from typing import Tuple
from plato.models.task import CustomEvalConfig, PlatoTask
from openai import AsyncOpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI()

class LLMJudgeResponseFormat(BaseModel):
  success: bool
  reason: str

async def llm_judge_eval_fn(data: dict, prompt: str) -> Tuple[bool, str]:
  response = await client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=[
      {"role": "system", "content": "Your job is to judge whether the given prompt is satisfied by the given data. If it is, return 'true'. If it is not, return 'false'. Also include the reason for the score."},
      {"role": "user", "content": f"prompt: {prompt}\n orders: {json.dumps(data['state']['consumer_orders'])}"},
    ],
    response_format=LLMJudgeResponseFormat
  )
  return response.choices[0].message.parsed.success, response.choices[0].message.parsed.reason

craigslist_tasks = [
    PlatoTask(
        name="find_apartment_with_criteria",
        prompt="Find a 2-bedroom apartment in San Francisco under $3000/month that allows pets and has in-unit laundry",
        start_url="https://www.craigslist.org",
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Found listing should be in San Francisco, have 2 bedrooms, cost less than $3000, allow pets, and have in-unit laundry.")
        )
    ),
    PlatoTask(
        name="negotiate_furniture_price",
        prompt="Find a used leather couch listed for over $500. Draft a message to the seller to negotiate at least 20% off the listing price.",
        start_url="https://www.craigslist.org", 
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have found a suitable couch and drafted a negotiation message for at least 20% off.")
        )
    ),
    PlatoTask(
        name="complex_car_search",
        prompt="Find a used Toyota or Honda sedan between 2015-2020 with less than 100k miles, priced under $15000. For 3 such listings, draft a message to ask about maintenance history.",
        start_url="https://www.craigslist.org",
        env_id="craigslist", 
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have found qualifying cars and drafted messages for 3 different sellers asking about maintenance history.")
        )
    ),
    PlatoTask(
        name="gig_application",
        prompt="Find a web development gig job posting. Draft a compelling response highlighting relevant skills and including a portfolio link, ready for submission.",
        start_url="https://www.craigslist.org",
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have found a web dev gig and drafted an application with skills and portfolio.")
        )
    )
    ,
    PlatoTask(
        name="multi_item_garage_sale",
        prompt="Search for garage sales in a specific neighborhood, identify one selling both vintage furniture and electronics. Draft a plan to negotiate bundle pricing for at least 3 items and to arrange same-day pickup.",
        start_url="https://www.craigslist.org",
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have found a garage sale with both furniture and electronics, and drafted a plan for negotiating bundle pricing for 3+ items and arranging pickup.")
        )
    ),
    PlatoTask(
        name="competitive_rental_application",
        prompt="Find a newly listed 1-bedroom apartment in a desirable neighborhood under $2500. Draft a rental application, including a compelling cover letter and placeholder for proof of income/credit score, as if to be submitted within 2 hours of posting.",
        start_url="https://www.craigslist.org",
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom", 
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have found a recent listing and drafted a complete application with cover letter and noted need for documentation, simulating a quick submission.")
        )
    ),
    PlatoTask(
        name="specialized_equipment_purchase",
        prompt="Find a professional-grade camera setup including a DSLR body and at least 2 lenses. Draft messages to verify authenticity by requesting serial numbers and original purchase receipts, and to negotiate a package deal with warranty transfer.",
        start_url="https://www.craigslist.org",
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have found complete camera setup, and drafted messages to verify authenticity, negotiate warranty transfer and package pricing.")
        )
    ),
    PlatoTask(
        name="event_venue_search",
        prompt="Find a venue for a 100-person wedding reception, available on a Saturday in the next 6 months, with parking, catering kitchen, and outdoor space. Draft messages to at least 3 venues to compare pricing and availability.",
        start_url="https://www.craigslist.org",
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have found suitable venues meeting all criteria and drafted messages to 3+ locations to inquire about comparative pricing and availability.")
        )
    ),
    PlatoTask(
        name="skilled_trade_hiring",
        prompt="Draft a detailed job listing for an experienced plumber, including licensing requirements, salary range, and benefits. Outline a plan to screen potential responses, request references, and schedule interviews with qualified candidates if the job were posted.",
        start_url="https://www.craigslist.org",
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have drafted a comprehensive job posting and outlined a plan for screening and scheduling qualified candidates.")
        )
    ),
    PlatoTask(
        name="multi_property_investment",
        prompt="Research and compare at least 5 investment properties under $500k, calculate potential ROI based on rental market rates. For the top 3 candidates, draft messages to owners to request property condition reports and tax history, and to inquire about scheduling viewings.",
        start_url="https://www.craigslist.org",
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have analyzed 5+ properties, performed ROI calculations, and drafted messages to request property condition reports, tax history and inquire about viewings for top 3 candidates.")
        )
    )
]

craigslist_eval_tasks = [
    PlatoTask(
        name="complex_multi_city_relocation",
        prompt="Find and compare housing options across 5 different cities, each requiring: 3+ bedroom house, under $3000/month, within 10 minutes of highly rated schools, low crime rate, and good public transit. Create a detailed spreadsheet comparing cost of living, commute times, and neighborhood amenities. For all viable options, draft messages to landlords to inquire about early move-in dates and pet policies.",
        start_url="https://www.craigslist.org",
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have comprehensive analysis of multiple cities with detailed comparisons and drafted messages to landlords for inquiries about move-in and pet policies.")
        )
    ),
    PlatoTask(
        name="vintage_car_restoration_project",
        prompt="Source all necessary parts for a complete 1967 Mustang restoration, including: matching numbers engine block, original interior upholstery, period-correct wheels and tires, and all chrome trim pieces. Draft messages to verify authenticity of all parts and to negotiate bulk pricing. Research options and draft a plan for climate-controlled transportation for delicate components.",
        start_url="https://www.craigslist.org", 
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have found all parts, drafted messages to verify authenticity and negotiate bulk pricing, and planned for specialized shipping with proper documentation.")
        )
    ),
    PlatoTask(
        name="multi_vendor_event_coordination",
        prompt="Coordinate a weekend craft fair by finding and vetting 50 artisan vendors, securing food trucks, arranging rental equipment (tents, tables, chairs, portable restrooms), and booking entertainment. Draft negotiation points for rates with vendors and service providers, create detailed layout plans, and draft load-in schedules. Research and list necessary permits and insurance coverage.",
        start_url="https://www.craigslist.org",
        env_id="craigslist", 
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have successfully identified potential vendors and services, drafted negotiation points, created plans, and researched legal requirements for a large event.")
        )
    ),
    PlatoTask(
        name="commercial_kitchen_equipment_acquisition",
        prompt="Source complete equipment for a new restaurant kitchen including: commercial grade ovens, refrigeration, dishwashing system, ventilation hood, and prep stations. Verify all equipment meets health code requirements. Draft inquiries for arranging certified installation and for negotiating warranties. Draft a plan to coordinate delivery timing and create a detailed installation schedule.",
        start_url="https://www.craigslist.org",
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have sourced code-compliant equipment, drafted inquiries for installation and warranties, and drafted plans for logistics.")
        )
    ),
    PlatoTask(
        name="film_production_equipment_rental",
        prompt="Source equipment for a 2-week film shoot including: multiple camera packages, lighting rigs, sound equipment, grip gear, and production vehicles. Verify insurance coverage. Identify options for backup equipment. Draft plans to coordinate pickup/delivery schedules. Draft negotiation points for rates with multiple vendors while ensuring all equipment is compatible.",
        start_url="https://www.craigslist.org",
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have identified necessary equipment, options for backup, drafted logistical plans, and drafted negotiation points.")
        )
    ),
    PlatoTask(
        name="emergency_disaster_relief_housing",
        prompt="Following a natural disaster, locate and secure temporary housing for 20 displaced families within 48 hours. Requirements include: pet-friendly options, accessibility features, proximity to medical facilities, and flexible lease terms. Draft a plan to coordinate with insurance adjusters and draft messages to negotiate immediate move-in terms with housing providers.",
        start_url="https://www.craigslist.org",
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have rapidly identified suitable housing options meeting all critical requirements for multiple families, and drafted plans/messages for coordination and negotiation.")
        )
    ),
    PlatoTask(
        name="specialized_manufacturing_equipment",
        prompt="Source industrial manufacturing equipment including: CNC machines, industrial 3D printers, and automated assembly line components. Verify operational history. Draft plans for technical inspections. Draft messages to negotiate maintenance contracts. Plan for specialized transportation with proper insurance coverage.",
        start_url="https://www.craigslist.org",
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have secured verified equipment with proper documentation, drafted plans for inspections, drafted messages for maintenance contracts, and planned specialized transport arrangements.")
        )
    ),
    PlatoTask(
        name="multi_generation_estate_sale",
        prompt="Catalog and price 200+ items from a multi-generation estate including: antique furniture, vintage jewelry, rare books, art collections, and historical documents. Research market values, identify methods for authenticating valuable pieces and arranging professional appraisals. Draft a plan to coordinate viewing appointments with serious collectors (e.g., draft template messages for outreach).",
        start_url="https://www.craigslist.org",
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have properly cataloged, researched market values for items, identified authentication/appraisal methods, and drafted a plan for coordinating with collectors.")
        )
    ),
    PlatoTask(
        name="sustainable_farm_equipment_acquisition",
        prompt="Source complete equipment setup for a 50-acre organic farm including: tractors, irrigation systems, greenhouse materials, and specialized harvesting equipment. Verify organic certification compliance. Draft plans for soil testing. Draft negotiation points for multiple vendors. Create a detailed implementation timeline.",
        start_url="https://www.craigslist.org",
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have identified compliant equipment, drafted plans for soil testing, drafted negotiation points, and created implementation planning with proper certification considerations.")
        )
    ),
    PlatoTask(
        name="historic_building_renovation_materials",
        prompt="Source period-appropriate materials for historic building renovation including: architectural salvage, vintage fixtures, period-correct building materials, and specialized craftsman tools. Verify authenticity and age of materials. Research process for architectural review approval. Identify how to coordinate with preservation specialists and draft initial communication templates if necessary.",
        start_url="https://www.craigslist.org",
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have sourced authentic materials meeting preservation requirements, researched approval processes, identified coordination methods with specialists, and has proper documentation.")
        )
    )
]


all_tasks = craigslist_tasks 