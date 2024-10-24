
from typing import Optional
from urllib import response
from pydantic import BaseModel
import requests
from functools import wraps
from datetime import datetime

BASE_URL = "https://api.plato.so"
# BASE_URL = "http://api.localhost:25565"


class PlatoConfig(BaseModel):
  api_key: str
  base_url: Optional[str] = BASE_URL


class PlatoSession:
  def __init__(self, config: PlatoConfig):
    self.config = config
    self.session_id = None

  def make_request(self, method: str, path: str, **kwargs):
    pass

  def start(self) -> 'PlatoSession':
    # get a browser connection
    # then connect to server with socketio connection
    print('calling with', self.config.base_url, self.config.api_key)
    response = requests.post(
      f"{self.config.base_url}/start-session",
      headers={"Authorization": f"Bearer {self.config.api_key}"},
      json={}
    )
    response.raise_for_status()
    self.session_id = response.json()["session_id"]
    return self

  def end(self):
    response = requests.post(
      f"{self.config.base_url}/end-session",
      headers={"Authorization": f"Bearer {self.config.api_key}"},
      json={"session_id": self.session_id}
    )
    response.raise_for_status()

  def navigate(self, url: str):
    action = {
      "id": f'{int(datetime.now().timestamp() * 1000)}-navigate',
      "type": "navigate",
      "parameter": {
        "type": "navigate",
        "name": url,
        "isArray": False
      }
    }
    response = requests.post(
      f"{self.config.base_url}/run-action",
      headers={"Authorization": f"Bearer {self.config.api_key}"},
      json={
        "session_id": self.session_id,
        "action": action
      }
    )
    response.raise_for_status()
    return response.json()

  def act(self, action: str, **kwargs):
    action = {
      "id": f'{int(datetime.now().timestamp() * 1000)}-act',
      "type": "act",
      "parameter": {
        "type": "act",
        "name": action,
        "isArray": False
      }
    }
    response = requests.post(
      f"{self.config.base_url}/run-action",
      headers={"Authorization": f"Bearer {self.config.api_key}"},
      json={
        "session_id": self.session_id,
        "action": action
      },
      timeout=360
    )
    response.raise_for_status()
    return response.json()

  def type(self, text: str):
    action = {
      "id": f'{int(datetime.now().timestamp() * 1000)}-input',
      "type": "action",
      "parameter": {
        "type": "input",
        "name": text,
        "isArray": False
      }
    }
    response = requests.post(
      f"{self.config.base_url}/run-action",
      headers={"Authorization": f"Bearer {self.config.api_key}"},
      json={
        "session_id": self.session_id,
        "action": action
      },
      timeout=60
    )
    response.raise_for_status()
    return response.json()
  def extract(self, url: str, **kwargs):
    pass

  def monitor(self, url: str, **kwargs):
    pass

  def job(self, job_id: str, **kwargs):
    pass



class PlatoClient:
  @staticmethod
  def start_session(config: PlatoConfig) -> PlatoSession:
    return PlatoSession(config).start()

