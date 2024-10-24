
from typing import Optional
from pydantic import BaseModel

BASE_URL = "https://api.plato.so"

class PlatoSession:
  def __init__(self, session_id: str):
    self.session_id = session_id

  async def start(self):
    # get a browser connection
    # then connect to server with socketio connection
    pass

  async def act(self, action: str, **kwargs):
    pass

  async def extract(self, url: str, **kwargs):
    pass

  async def monitor(self, url: str, **kwargs):
    pass

  async def job(self, job_id: str, **kwargs):
    pass


class PlatoConfig(BaseModel):
  api_key: str
  base_url: Optional[str] = BASE_URL

class PlatoClient:
  @staticmethod
  async def start_session(config: PlatoConfig) -> PlatoSession:
    return await PlatoSession(session_id="123").start()

