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




# Tasks that should have only one correct answer with zero ambiguity
specific_easy_tasks = [
    PlatoTask(
        name="order_plain_pizza_papa_johns",
        prompt="order a medium pizza from papa johns with no toppings",
        start_url="https://www.doordash.com",
        public_id="41883c82-bf21-4472-8a0f-4b143759d385",
        env_id="doordash",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with nothing but 1 medium pizza from papa johns with no toppings"),
        )
    ),
    PlatoTask(
        name="order_pork_bao_dumpling_story",
        prompt="order juicy pork bao from Dumpling story",
        public_id="7dd7b69e-a819-4377-8bb1-85caedf91939",
        start_url="https://www.doordash.com",
        env_id="doordash",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with nothing but 1 juicy pork bao from Dumpling story"),
        )
    ),
    PlatoTask(
        name="order_classic_grandma_pie_punks",
        prompt="order a Classic Grandma from pie punks",
        public_id="565757e4-9b9b-4777-a307-69baf5389514",
        start_url="https://www.doordash.com",
        env_id="doordash",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with nothing but 1 Classic Grandma from pie punks"),
        )
    ),
    PlatoTask(
        name="order_chicken_sandwiches_the_bird",
        prompt="order 2 fried chicken sandwhiches from The Bird",
        public_id="8cfd525b-21d7-4cab-84f9-ceb1c2497980",
        start_url="https://www.doordash.com",
        env_id="doordash",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with nothing but 2 fried chicken sandwhiches from The Bird"),
        )
    ),
    PlatoTask(
        name="order_buffalo_wings_the_bird",
        prompt="order a 10 piece buffalo wings from The Bird",
        public_id="436fe8ac-0fdb-4574-a6a0-6a4a609d8b77",
        start_url="https://www.doordash.com",
        env_id="doordash",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with nothing but 10 piece buffalo wings from The Bird"),
        ),
    ),
    PlatoTask(
        name="order_shawarma_fries_popstar",
        prompt="order a large chicken shawarma fries from Popstar shawarma",
        public_id="66df817b-5c27-4146-b8ea-80ad99d33349",
        start_url="https://www.doordash.com",
        env_id="doordash",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with nothing but 1 large chicken shawarma fries from Popstar shawarma"),
        ),
    ),
    PlatoTask(
        name="order_boneless_wings_wingstop",
        prompt="order 10 boneless wings from Wingstop. I want only original hot flavour",
        public_id="3fe5d926-8b81-4ca2-a39c-befa8367c9c8",
        start_url="https://www.doordash.com",
        env_id="doordash",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with nothing but 10 boneless wings from Wingstop. I want only original hot flavour"),
        ),
    ),
    PlatoTask(
        name="order_pad_thai_osha",
        prompt="order chicken pad thai from OSHA Thai Restaurant with medium spice level.",
        public_id="ce761642-5807-4aea-a2e2-b323333f4d8c",
        start_url="https://www.doordash.com",
        env_id="doordash",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with nothing but 1 chicken pad thai from OSHA Thai Restaurant with medium spice level."),
        ),
    ),
    PlatoTask(
        name="order_chicken_salad_halal_cart",
        prompt="order a chicken over salad from Halal Cart SF",
        public_id="62c21dd7-da55-4fdf-9c90-ce5e021e3b92",
        start_url="https://www.doordash.com",
        env_id="doordash",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with nothing but 1 chicken over salad from Halal Cart SF"),
        ),
    ),
    PlatoTask(
        name="order_quesadilla_chisme",
        prompt="order a Chicken Quesadilla from Chisme",
        public_id="97e6afee-abbc-463d-96cd-76dd9da0f166",
        start_url="https://www.doordash.com",
        env_id="doordash",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with nothing but 1 Chicken Quesadilla from Chisme"),
        ),
    ),
    PlatoTask(
        name="order_noodle_soup_gai",
        prompt="order a Gai Noodle Soup from Gai Chicken Rice",
        public_id="d243b67f-1dd9-4585-9e99-7405226a6e10",
        start_url="https://www.doordash.com",
        env_id="doordash",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with nothing but 1 Gai Noodle Soup from Gai Chicken Rice"),
        ),
    ),
]

# Tasks that have only one correct answer but include multiple items or detailed specifications
multiple_items_specific_tasks = [
    # PlatoTask(
    #     name="order_pizza_and_drinks_papa_johns",
    #     prompt="buy a medium pizza from papa johns. get pepperoni and jalapenos. also get 2 cans of diet coke.",
    #     start_url="https://www.doordash.com",
    #     eval_config=CustomEvalConfig(
    #       type="custom",
    #       score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with nothing but 1 medium pizza from papa johns. get pepperoni and jalapenos. also get 2 cans of diet coke."),
    #     ),
    # ),
    PlatoTask(
        name="order_custom_poke_bowl",
        prompt="order a large poke bowl from Poke Bowl. For my sauce I want spicy mayo sauce. For protein I want crab. For my sides I want cucumber and carrot. For my base I want white rice. For toppings I want Sesame Seeds and Fried garlic chips.",
        start_url="https://www.doordash.com",
        public_id="74384e5f-8d7b-47b7-a25a-145e145a02e5",
        env_id="doordash",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with nothing but 1 large poke bowl from Poke Bowl. For my sauce I want spicy mayo sauce. For protein I want crab. For my sides I want cucumber and carrot. For my base I want white rice. For toppings I want Sesame Seeds and Fried garlic chips."),
        ),
    ),
    PlatoTask(
        name="order_souvla_salad_and_sides",
        prompt="order a chicken salad from Souvla. get dressing on the side and get no onions. also get a side of greek fries and a lemon soda.",
        start_url="https://www.doordash.com",
        public_id="093af440-b9fd-4f44-8ca0-e9d1b68fa2cc",
        env_id="doordash",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with nothing but 1 chicken salad from Souvla. get dressing on the side and get no onions. also get a side of greek fries and a lemon soda."),
        ),
    ),
    PlatoTask(
        name="order_custom_chipotle_burritos",
        prompt="get me 2 burritos from Chipotle. The first one should be white rice, black beans and chicken. With medium salsa, cheese and lettuce. The second one should be a brown rice, pinto beans and steak with hot salsa, sour cream, guacamole, cheese and lettuce.",
        start_url="https://www.doordash.com",
        public_id="ab3e0322-52e3-4c88-9c47-70d210e288af",
        env_id="doordash",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with nothing but 2 burritos from Chipotle. The first one should be white rice, black beans and chicken. With medium salsa, cheese and lettuce. The second one should be a brown rice, pinto beans and steak with hot salsa, sour cream, guacamole, cheese and lettuce."),
        ),
    ),
    PlatoTask(
        name="order_pizza_and_sides_bellissimo",
        prompt="order an extra large pizza from Bellissimo Pizza. I want 3 toppings. 1. pepperoni 2. mushroom 3. pineapple. I also want a side of garlic bread and 3 bottles of water.",
        public_id="1793afe8-12c0-4cb9-9f8f-033f8879e716",
        start_url="https://www.doordash.com",
        env_id="doordash",
        eval_config=CustomEvalConfig(
          type="custom",
          score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with nothing but 1 extra large pizza from Bellissimo's. I want 3 toppings. 1. pepperoni 2. mushroom 3. pineapple. I also want a side of garlic bread and 3 bottles of water."),
        ),
    ),
]

# Tasks that have multiple possible correct answers based on constraints
# easy_open_ended_tasks = [
#     PlatoTask(
#         name="order_budget_shawarma",
#         prompt="buy shawarma that has has chicken and fries. It shouldn't have anything else in it. Also I don't want to spend more than 15 dollars",
#         start_url="https://www.doordash.com",
#         eval_config=CustomEvalConfig(
#           type="custom",
#           score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with nothing but 1 shawarma that has has chicken and fries. It shouldn't have anything else in it. Also I don't want to spend more than 15 dollars"),
#         ),
#     ),
#     PlatoTask(
#         name="order_premium_sushi",
#         prompt="buy sushi for 4 people from the highest rated sushi place in SF. money is no contraint. I want the best stuff.",
#         start_url="https://www.doordash.com",
#         eval_config=CustomEvalConfig(
#           type="custom",
#           score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with nothing but sushi for 4 people from the highest rated sushi place in SF. money is no contraint. I want the best stuff."),
#         ),
#     ),
#     PlatoTask(
#         name="order_quick_delivery_pizza",
#         prompt="get me a large pizza from a place that has at least 4.5 stars and can be delivered in less than 30 minutes. Get pepperoni and mushroom on it.",
#         start_url="https://www.doordash.com",
#         eval_config=CustomEvalConfig(
#           type="custom",
#           score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with nothing but a large pizza from a place that has at least 4.5 stars and can be delivered in less than 30 minutes. Get pepperoni and mushroom on it."),
#         ),
#     ),
# ]

# Tasks that require searching and filtering based on specific criteria
# search_and_filter_tasks = [
#   PlatoTask(
#     name="order_budget_pepperoni_pizza",
#     prompt="order a pepperoni pizza for a total cost of < 30",
#     start_url="https://www.doordash.com",
#     eval_config=CustomEvalConfig(
#       type="custom",
#       score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with nothing but 1 pepperoni pizza with a total cost less than $30"),
#     )
#   ),
#   PlatoTask(
#     name="order_highly_rated_pad_thai",
#     prompt="order pad thai from somewhere with a rating of at least 4.7 and a delivery fee of less than $2.00",
#     start_url="https://www.doordash.com",
#     eval_config=CustomEvalConfig(
#       type="custom",
#       score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with nothing but 1 pad thai from a restaurant with rating >= 4.7 and delivery fee < $2.00"),
#     )
#   ),
#   PlatoTask(
#     name="order_quick_buffalo_wings",
#     prompt="order buffalo wings with a rating of at least 4.8 and a delivery time of less than 30 minutes",
#     start_url="https://www.doordash.com",
#     eval_config=CustomEvalConfig(
#       type="custom",
#       score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with nothing but buffalo wings from a restaurant with rating >= 4.8 and delivery time < 30 minutes"),
#     )
#   ),
#   PlatoTask(
#     name="order_indian_no_delivery_fee",
#     prompt="order butter chicken, butter naan, and plain rice from an indian restaurant with no delivery fees",
#     start_url="https://www.doordash.com",
#     eval_config=CustomEvalConfig(
#       type="custom",
#       score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with butter chicken, butter naan, and plain rice from an indian restaurant with $0 delivery fee"),
#     )
#   ),
# ]

# Tasks that require ordering from specific restaurants
specific_restaurant_tasks = [
  PlatoTask(
    name="order_little_caesars_pizza",
    prompt="Order thin crust cheese pizza from Little Caesars",
    start_url="https://www.doordash.com",
    public_id="order_little_caesars_pizza",
    env_id="doordash",
    eval_config=CustomEvalConfig(
      type="custom",
      score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with nothing but 1 thin crust cheese pizza from Little Caesars"),
    )
  ),
  PlatoTask(
    name="order_proposition_wings",
    prompt="Order buffalo wings from Proposition Chicken",
    public_id="43dc71d8-58e6-483d-ac0b-5c15385a4c8f",
    start_url="https://www.doordash.com",
    env_id="doordash",
    eval_config=CustomEvalConfig(
      type="custom",
      score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with nothing but buffalo wings from Proposition Chicken"),
    )
  ),
  PlatoTask(
    name="order_north_beach_pizza",
    prompt="Order an extra large pepperoni pizza from North Beach pizza",
    public_id="94053ed7-3bb5-40c5-a176-b221b129a312",
    start_url="https://www.doordash.com",
    env_id="doordash",
    eval_config=CustomEvalConfig(
      type="custom",
      score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with nothing but 1 extra large pepperoni pizza from North Beach pizza"),
    )
  ),
]

# Tasks that require advanced customizations from specific restaurants
advanced_customization_tasks = [
  PlatoTask(
    name="order_mcdonalds_nuggets_meal_2",
    prompt="Order a 10 piece Chicken McNuggets from McDonalds meal with a large coke, spicy buffalo sauce and hot mustard sauce",
    start_url="https://www.doordash.com",
    public_id="4dd76fd4-54e1-4969-add6-b6617808a651",
    env_id="doordash",
    eval_config=CustomEvalConfig(
      type="custom",
      score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with nothing but 1 10-piece Chicken McNuggets meal from McDonalds with large coke and hot mustard sauce"),
    )
  ),
  PlatoTask(
    name="order_mcdonalds_custom_burger",
    prompt="Order a Double Cheeseburger from McDonalds with no Onions and extra cheese",
    public_id="029e4108-1f38-4a2f-a7e8-5e684140c34a",
    start_url="https://www.doordash.com",
    env_id="doordash",
    eval_config=CustomEvalConfig(
      type="custom",
      score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with nothing but 1 Double Cheeseburger from McDonalds with no onions and extra cheese"),
    )
  ),
  PlatoTask(
    name="order_feng_cha_milk_tea",
    prompt="Order a milk tea from Feng Cha with a jasmine green tea base, Regular Ice, 50% sweet, oat milk, boba pearls and grass jelly",
    public_id="5b39329f-ed68-47d2-a6b0-c96763763598",
    start_url="https://www.doordash.com",
    env_id="doordash",
    eval_config=CustomEvalConfig(
      type="custom",
      score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with nothing but 1 milk tea from Feng Cha with jasmine green tea base, Regular Ice, 50% sweet, oat milk, boba pearls and grass jelly"),
    )
  ),
  PlatoTask(
    name="order_ea_cafe_poke",
    prompt="Get a poke bowl from Ea Cafe with spicy crab meat cucumber, sweet corn, miso sauce, cabbage, and pineapple",
    public_id="853c5c3e-9322-478a-86bc-67acd5da1505",
    start_url="https://www.doordash.com",
    env_id="doordash",
    eval_config=CustomEvalConfig(
      type="custom",
      score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with nothing but 1 poke bowl from Ea Cafe with spicy crab meat cucumber, sweet corn, miso sauce, cabbage, and pineapple"),
    )
  ),
  PlatoTask(
    name="order_popeyes_combo_2",
    prompt="Order a 3Pc spicy Tenders Combo from Popeyes with blackened ranch sauce, cajun fries and a diet coke",
    public_id="d3c41375-71c4-4f00-85a5-5e4c4fa7999d",
    start_url="https://www.doordash.com",
    env_id="doordash",
    eval_config=CustomEvalConfig(
      type="custom",
      score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with nothing but 1 3Pc spicy Tenders Combo from Popeyes with blackened ranch sauce, cajun fries and a diet coke and a biscuit"),
    )
  ),
  PlatoTask(
    name="order_kfc_fan_box",
    public_id="2307f342-4a27-4b44-960c-40ab9d74c0bf",
    prompt="Order a Fan Favorite Box from KFC with extra crispy chicken, 2x gravy and 2x ranch,4 large Starrys, and a 10 piece cherry pie popper with a plate",
    start_url="https://www.doordash.com",
    env_id="doordash",
    eval_config=CustomEvalConfig(
      type="custom",
      score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with nothing but 1 Fan Favorite Box from KFC with extra crispy chicken, 2x gravy, 2x ranch, 4 large Starrys, and a 10 piece cherry pie popper with a plate"),
    )
  ),
]

# Tasks that require ordering multiple items from specific restaurants
multiple_items_tasks = [
  PlatoTask(
    name="order_papa_johns_combo_2_liters",
    public_id="06127157-8ebc-4c65-97ab-cba3bb86a471",
    prompt="Order a cheese pizza and a 2 liter pepsi from papa johns",
    start_url="https://www.doordash.com",
    env_id="doordash",
    eval_config=CustomEvalConfig(
      type="custom",
      score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with nothing but 1 pizza with no toppings and a 2 liter bottle of pepsi from papa johns"),
    )
  ),
  PlatoTask(
    name="order_dumpling_time_combo",
    public_id="00058649-92cb-48ec-92bf-5e320edd0f5f",
    prompt="Order Steamed BBQ Pork Bao, Shrimp & Pork Siu Mai, Tom Yum, and Crispy Sesame Tofu Squares from Dumpling Time",
    start_url="https://www.doordash.com",
    env_id="doordash",
    eval_config=CustomEvalConfig(
      type="custom",
      score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with nothing but Steamed BBQ Pork Bao, Shrimp & Pork Siu Mai, Tom Yum, and Crispy Sesame Tofu Squares from Dumpling Time"),
    )
  ),
  PlatoTask(
    name="order_newa_indian_combo",
    public_id="ce3307dc-39dc-465b-8318-cec56c0527f6",
    prompt="Get 2 orders of Chicken Tikka Masalas, 2 Basmati Rices, 1 garlic naan and 1 plain naan from NEWA Nepalese Indian Resturant",
    start_url="https://www.doordash.com",
    env_id="doordash",
    eval_config=CustomEvalConfig(
      type="custom",
      score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with nothing but 2 Chicken Tikka Masalas, 2 Basmati Rices, 1 garlic naan and 1 plain naan from NEWA Nepalese Indian Resturant"),
    )
  ),
]

# Bonus tasks with special requirements
bonus_tasks = [
  # PlatoTask(
  #   name="reorder_shawarma_with_drink",
  #   prompt="re-order the last shawarma I got. also add a diet coke",
  #   start_url="https://www.doordash.com",
  #   eval_config=CustomEvalConfig(
  #     type="custom",
  #     score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order from Popstar Shawarma with a chicken shawarma fries and a diet coke"),
  #   )
  # ),
  PlatoTask(
    name="order_rt_rotisserie_with_tip",
    prompt="Order a Umami Fries from RT Rotisserie and tip 30%",
    start_url="https://www.doordash.com",
    public_id="00058649-92cb-48ec-92bf-5e320edd0f5f",
    env_id="doordash",
    eval_config=CustomEvalConfig(
      type="custom",
      score_fn=lambda x: llm_judge_eval_fn(x, "There should be 1 order with Umami Fries from RT Rotisserie and a 30% tip"),
    )
  ),
]



all_tasks = specific_easy_tasks + multiple_items_specific_tasks + specific_restaurant_tasks + advanced_customization_tasks + multiple_items_tasks + bonus_tasks
