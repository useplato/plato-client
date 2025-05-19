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
        prompt="Find a used leather couch listed for over $500 and negotiate with the seller to get at least 20% off the listing price",
        start_url="https://www.craigslist.org", 
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have messaged seller about a leather couch and negotiated at least 20% below the original price.")
        )
    ),
    PlatoTask(
        name="complex_car_search",
        prompt="Find a used Toyota or Honda sedan between 2015-2020 with less than 100k miles, priced under $15000, and message 3 different sellers to ask about maintenance history",
        start_url="https://www.craigslist.org",
        env_id="craigslist", 
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have found qualifying cars and messaged 3 different sellers asking about maintenance history.")
        )
    ),
    PlatoTask(
        name="gig_application",
        prompt="Find a web development gig job posting, create a compelling response highlighting relevant skills, and submit application with a portfolio link",
        start_url="https://www.craigslist.org",
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have found a web dev gig and submitted an application with skills and portfolio.")
        )
    )
    ,
    PlatoTask(
        name="multi_item_garage_sale",
        prompt="Search for garage sales in a specific neighborhood, identify one selling both vintage furniture and electronics, negotiate bundle pricing for at least 3 items, and arrange same-day pickup",
        start_url="https://www.craigslist.org",
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have found a garage sale with both furniture and electronics, negotiated bundle pricing for 3+ items, and arranged pickup.")
        )
    ),
    PlatoTask(
        name="competitive_rental_application",
        prompt="Find a newly listed 1-bedroom apartment in a desirable neighborhood under $2500, submit a rental application within 2 hours of posting, including a compelling cover letter and proof of income/credit score",
        start_url="https://www.craigslist.org",
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom", 
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have found a recent listing, submitted complete application with cover letter and documentation quickly.")
        )
    ),
    PlatoTask(
        name="specialized_equipment_purchase",
        prompt="Find a professional-grade camera setup including a DSLR body and at least 2 lenses, verify authenticity by requesting serial numbers and original purchase receipts, and negotiate a package deal with warranty transfer",
        start_url="https://www.craigslist.org",
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have found complete camera setup, verified authenticity, and negotiated warranty transfer and package pricing.")
        )
    ),
    PlatoTask(
        name="event_venue_search",
        prompt="Find a venue for a 100-person wedding reception, available on a Saturday in the next 6 months, with parking, catering kitchen, and outdoor space. Contact at least 3 venues to compare pricing and availability",
        start_url="https://www.craigslist.org",
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have found suitable venues meeting all criteria and obtained comparative pricing from 3+ locations.")
        )
    ),
    PlatoTask(
        name="skilled_trade_hiring",
        prompt="Post a detailed job listing for an experienced plumber, including licensing requirements, salary range, and benefits. Screen initial responses, request references, and schedule interviews with qualified candidates",
        start_url="https://www.craigslist.org",
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have created comprehensive job posting and effectively screened and scheduled qualified candidates.")
        )
    ),
    PlatoTask(
        name="multi_property_investment",
        prompt="Research and compare at least 5 investment properties under $500k, calculate potential ROI based on rental market rates, contact owners for property condition reports and tax history, and schedule viewings for top 3 candidates",
        start_url="https://www.craigslist.org",
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have analyzed 5+ properties, performed ROI calculations, obtained detailed information, and arranged viewings.")
        )
    )
]

craigslist_eval_tasks = [
    PlatoTask(
        name="complex_multi_city_relocation",
        prompt="Find and compare housing options across 5 different cities, each requiring: 3+ bedroom house, under $3000/month, within 10 minutes of highly rated schools, low crime rate, and good public transit. Create a detailed spreadsheet comparing cost of living, commute times, and neighborhood amenities. Contact landlords to negotiate early move-in dates and pet policies for all viable options.",
        start_url="https://www.craigslist.org",
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have comprehensive analysis of multiple cities with detailed comparisons and successful landlord negotiations.")
        )
    ),
    PlatoTask(
        name="vintage_car_restoration_project",
        prompt="Source all necessary parts for a complete 1967 Mustang restoration, including: matching numbers engine block, original interior upholstery, period-correct wheels and tires, and all chrome trim pieces. Verify authenticity of all parts, negotiate bulk pricing, and arrange climate-controlled transportation for delicate components.",
        start_url="https://www.craigslist.org", 
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have found all authentic parts with proper documentation and arranged specialized shipping.")
        )
    ),
    PlatoTask(
        name="multi_vendor_event_coordination",
        prompt="Coordinate a weekend craft fair by finding and vetting 50 artisan vendors, securing food trucks, arranging rental equipment (tents, tables, chairs, portable restrooms), and booking entertainment. Negotiate rates, create detailed layout plans, and establish load-in schedules while ensuring proper permits and insurance coverage.",
        start_url="https://www.craigslist.org",
        env_id="craigslist", 
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have successfully coordinated all vendors, logistics, and legal requirements for large event.")
        )
    ),
    PlatoTask(
        name="commercial_kitchen_equipment_acquisition",
        prompt="Source complete equipment for a new restaurant kitchen including: commercial grade ovens, refrigeration, dishwashing system, ventilation hood, and prep stations. Verify all equipment meets health code requirements, arrange certified installation, and negotiate warranties. Must coordinate delivery timing and create detailed installation schedule.",
        start_url="https://www.craigslist.org",
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have sourced code-compliant equipment with installation plans and warranty coverage.")
        )
    ),
    PlatoTask(
        name="film_production_equipment_rental",
        prompt="Source equipment for a 2-week film shoot including: multiple camera packages, lighting rigs, sound equipment, grip gear, and production vehicles. Verify insurance coverage, arrange backup equipment, coordinate pickup/delivery schedules, and negotiate rates with multiple vendors while ensuring all equipment is compatible.",
        start_url="https://www.craigslist.org",
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have secured all necessary equipment with backup options and coordinated logistics.")
        )
    ),
    PlatoTask(
        name="emergency_disaster_relief_housing",
        prompt="Following a natural disaster, locate and secure temporary housing for 20 displaced families within 48 hours. Requirements include: pet-friendly options, accessibility features, proximity to medical facilities, and flexible lease terms. Coordinate with insurance adjusters and negotiate immediate move-in terms.",
        start_url="https://www.craigslist.org",
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have rapidly secured suitable housing options meeting all critical requirements for multiple families.")
        )
    ),
    PlatoTask(
        name="specialized_manufacturing_equipment",
        prompt="Source industrial manufacturing equipment including: CNC machines, industrial 3D printers, and automated assembly line components. Verify operational history, arrange technical inspections, negotiate maintenance contracts, and coordinate specialized transportation with proper insurance coverage.",
        start_url="https://www.craigslist.org",
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have secured verified equipment with proper documentation and specialized transport arrangements.")
        )
    ),
    PlatoTask(
        name="multi_generation_estate_sale",
        prompt="Catalog and price 200+ items from a multi-generation estate including: antique furniture, vintage jewelry, rare books, art collections, and historical documents. Research market values, authenticate valuable pieces, arrange professional appraisals, and coordinate viewing appointments with serious collectors.",
        start_url="https://www.craigslist.org",
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have properly cataloged, authenticated, and priced items while coordinating with collectors.")
        )
    ),
    PlatoTask(
        name="sustainable_farm_equipment_acquisition",
        prompt="Source complete equipment setup for a 50-acre organic farm including: tractors, irrigation systems, greenhouse materials, and specialized harvesting equipment. Verify organic certification compliance, arrange soil testing, negotiate with multiple vendors, and create detailed implementation timeline.",
        start_url="https://www.craigslist.org",
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have secured compliant equipment with proper certification and implementation planning.")
        )
    ),
    PlatoTask(
        name="historic_building_renovation_materials",
        prompt="Source period-appropriate materials for historic building renovation including: architectural salvage, vintage fixtures, period-correct building materials, and specialized craftsman tools. Verify authenticity and age of materials, arrange architectural review approval, and coordinate with preservation specialists.",
        start_url="https://www.craigslist.org",
        env_id="craigslist",
        eval_config=CustomEvalConfig(
            type="custom",
            score_fn=lambda x: llm_judge_eval_fn(x, "Should have sourced authentic materials meeting preservation requirements with proper documentation.")
        )
    )
]


all_tasks = craigslist_tasks 