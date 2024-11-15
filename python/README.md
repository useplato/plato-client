# Plato Client


```python
from plato import Plato
from pydantic import BaseModel

class Company(BaseModel):
    name: str
    description: str
    img_url: str
    tags: list[str]


class Companies(BaseModel):
    companies: list[Company]

plato = Plato(api_key="YOUR_PLATO_API_KEY")

with plato.start_session() as session:
  session.navigate("https://ycombinator.com/companies")
  response = session.extract(description="all of the companies on the page", response_format=Companies)
  for company in response.companies:
    print(company.name, company.description, company.img_url, company.tags)

```

