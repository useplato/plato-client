# Plato SDK


## Usage
```
class Task(BaseModel):
    ...

async with env := plato.make(ENV_ID):
    cdp_url = env.cdp_url
    
    # connect to browser and do modifications

   # get state
    state_mutations: dict = env.get_state()

    # evaluate

    ...

```