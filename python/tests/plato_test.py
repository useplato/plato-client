import asyncio
from plato.plato_client import PlatoClient, PlatoConfig

async def test_plato_client_start_session():
  config = PlatoConfig(api_key="22493513-f909-4fef-8aaf-8af2c46dcf1c")
  session = PlatoClient.start_session(config)

  print(session)

  session.end()


if __name__ == "__main__":
  asyncio.run(test_plato_client_start_session())
