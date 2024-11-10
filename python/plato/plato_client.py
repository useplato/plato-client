
import enum
from typing import Optional
from urllib import response
import uuid
from pydantic import BaseModel
import requests
from functools import wraps
from datetime import datetime

# BASE_URL = "https://api.plato.so"
# BROWSER_BASE_URL = "https://chrome.plato.so"
BASE_URL = "http://api.localhost:25565"
BROWSER_BASE_URL = "ws://localhost:25565"


class ParamType(str, enum.Enum):
  TEXT = 'text'
  NUMBER = 'number'
  BOOLEAN = 'boolean'
  OBJECT = 'object'
  DATE = 'date'
  IMAGE = 'image'

class ExtractParameter(BaseModel):
  name: str
  description: Optional[str] = ""
  type: ParamType
  isArray: bool = False
  elementHint: Optional[dict] = None
  subParameters: Optional[list['ExtractParameter']]


class PlatoConfig(BaseModel):
  api_key: str
  base_url: Optional[str] = BASE_URL


class PlatoSession:
  def __init__(self, config: PlatoConfig):
    self.config = config
    self.session_id = None

  @property
  def browser_ws_url(self):
    return f"{BROWSER_BASE_URL}/ws?session_id={self.session_id}"

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
    return response.json()

  def navigate(self, url: str):
    response = requests.post(
      f"{self.config.base_url}/navigate",
      headers={"Authorization": f"Bearer {self.config.api_key}"},
      json={
        "session_id": self.session_id,
        "url": url
      }
    )
    response.raise_for_status()
    return response.json()

  def click(self, description: str):
    response = requests.post(
      f"{self.config.base_url}/click",
      headers={"Authorization": f"Bearer {self.config.api_key}"},
      json={
        "session_id": self.session_id,
        "description": description
      }
    )
    response.raise_for_status()
    return response.json()


  def type(self, text: str):
    response = requests.post(
      f"{self.config.base_url}/type",
      headers={"Authorization": f"Bearer {self.config.api_key}"},
      json={
        "session_id": self.session_id,
        "text": text
      }
    )
    response.raise_for_status()
    return response.json()

  def extract(self, description: str, schema: ExtractParameter):
    response = requests.post(
      f"{self.config.base_url}/extract",
      headers={"Authorization": f"Bearer {self.config.api_key}"},
      json={
        "session_id": self.session_id,
        "description": description,
        "schema": schema.model_dump()
      }
    )
    response.raise_for_status()
    return response.json()


  def monitor(self, url: str, **kwargs):
    pass

  def job(self, job_id: str, **kwargs):
    pass



class PlatoClient:
  @staticmethod
  def start_session(config: PlatoConfig) -> PlatoSession:
    return PlatoSession(config).start()

