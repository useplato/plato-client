from plato.models.task import PlatoTask, StateMutationMatchEvalConfig

# Tasks that should have only one correct answer with zero ambiguity
specific_easy_tasks = [
    PlatoTask(
        name="order_plain_pizza_papa_johns",
        prompt="order a medium pizza from papa johns with no toppings",
        start_url="https://www.doordash.com",
        eval_config=StateMutationMatchEvalConfig(
            state_mutations=[
                (
                    "browser.url",
                    "https://www.doordash.com/menu/papa-johns-pizza-san-francisco-ca/100000000000000000000000",
                ),
            ]
        ),
    ),
    PlatoTask(
        name="order_pork_bao_dumpling_story",
        prompt="order juicy pork bao from Dumpling story",
        start_url="https://www.doordash.com",
    ),
    PlatoTask(
        name="order_classic_grandma_pie_punks",
        prompt="order a Classic Grandma from pie punks",
        start_url="https://www.doordash.com",
    ),
    PlatoTask(
        name="order_chicken_sandwiches_the_bird",
        prompt="order 2 fried chicken sandwhiches from The Bird",
        start_url="https://www.doordash.com",
    ),
    PlatoTask(
        name="order_buffalo_wings_the_bird",
        prompt="order a 10 piece buffalo wings from The Bird",
        start_url="https://www.doordash.com",
    ),
    PlatoTask(
        name="order_shawarma_fries_popstar",
        prompt="order a large chicken shawarma fries from Popstar shawarma",
        start_url="https://www.doordash.com",
    ),
    PlatoTask(
        name="order_boneless_wings_wingstop",
        prompt="order 10 boneless wings from Wingstop. I want only original hot flavour",
        start_url="https://www.doordash.com",
    ),
    PlatoTask(
        name="order_pad_thai_osha",
        prompt="order chicken pad thai from OSHA Thai Restaurant with medium spice level.",
        start_url="https://www.doordash.com",
    ),
    PlatoTask(
        name="order_chicken_salad_halal_cart",
        prompt="order a chicken over salad from Halal Cart SF",
        start_url="https://www.doordash.com",
    ),
    PlatoTask(
        name="order_quesadilla_chisme",
        prompt="order a Chicken Quesadilla from Chisme",
        start_url="https://www.doordash.com",
    ),
    PlatoTask(
        name="order_noodle_soup_gai",
        prompt="order a Gai Noodle Soup from Gai Chicken Rice",
        start_url="https://www.doordash.com",
    ),
]

# Tasks that have only one correct answer but include multiple items or detailed specifications
multiple_items_specific_tasks = [
    PlatoTask(
        name="order_pizza_and_drinks_papa_johns",
        prompt="buy a medium pizza from papa johns. get pepperoni and jalapenos. also get 2 cans of diet coke.",
        start_url="https://www.doordash.com",
    ),
    PlatoTask(
        name="order_custom_poke_bowl",
        prompt="order a large poke bowl from Poke Bowl. For my sauce I want spicy mayo sauce. For protein I want crab. For my sides I want cucumber and carrot. For my base I want white rice. For toppings I want Sesame Seeds and Fried garlic chips.",
        start_url="https://www.doordash.com",
    ),
    PlatoTask(
        name="order_souvla_salad_and_sides",
        prompt="order a chicken salad from Souvla. get dressing on the side and get no onions. also get a side of greek fries and a lemon soda.",
        start_url="https://www.doordash.com",
    ),
    PlatoTask(
        name="order_custom_chipotle_burritos",
        prompt="get me 2 burritos from Chipotle. The first one should be white rice, black beans and chicken. With medium salsa, cheese and lettuce. The second one should be a brown rice, pinto beans and steak with hot salsa, sour cream, guacamole, cheese and lettuce.",
        start_url="https://www.doordash.com",
    ),
    PlatoTask(
        name="order_pizza_and_sides_bellissimos",
        prompt="order an extra large pizza from Bellissimo's. I want 3 toppings. 1. pepperoni 2. mushroom 3. pineapple. I also want a side of garlic bread and 3 bottles of water.",
        start_url="https://www.doordash.com",
    ),
]

# Tasks that have multiple possible correct answers based on constraints
easy_open_ended_tasks = [
    PlatoTask(
        name="order_budget_shawarma",
        prompt="buy shawarma that has has chicken and fries. It shouldn't have anything else in it. Also I don't want to spend more than 15 dollars",
        start_url="https://www.doordash.com",
    ),
    PlatoTask(
        name="order_premium_sushi",
        prompt="buy sushi for 4 people from the highest rated sushi place in SF. money is no contraint. I want the best stuff.",
        start_url="https://www.doordash.com",
    ),
    PlatoTask(
        name="order_quick_delivery_pizza",
        prompt="get me a large pizza from a place that has at least 4.5 stars and can be delivered in less than 30 minutes. Get pepperoni and mushroom on it.",
        start_url="https://www.doordash.com",
    ),
]
