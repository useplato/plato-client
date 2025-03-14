# Plato SDK


## Usage
```python
from plato import Plato

async def run():
    env = await client.make_environment("doordash")
    cdp_url = env.cdp_url

    # connect to browser and do modifications
    browser = await playwright.chromium.connect_over_cdp(cdp_url)

    # get state
    state_mutations: dict = env.get_state()

    # evaluate
    ...
