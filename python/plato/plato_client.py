
import enum
from typing import Optional
from urllib.parse import urlparse
from pydantic import BaseModel
import requests
from functools import wraps
from datetime import datetime

BASE_URL = "https://plato.so"

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


class Plato:
  def __init__(self, api_key: str, base_url: Optional[str] = BASE_URL):
    self.api_key = api_key
    self.base_url = base_url

  class PlatoSession:
    def __init__(self, plato: 'Plato'):
      self.plato = plato
      self.session_id = None

    @property
    def api_url(self):
      url = urlparse(self.plato.base_url)
      return f"{url.scheme}://api.{url.netloc}"

    @property
    def chrome_ws_url(self):
      url = urlparse(self.plato.base_url)
      return f"{'wss' if url.scheme == 'https' else 'ws'}://{url.netloc}/ws?session_id={self.session_id}"

    @property
    def browser_url(self):
      url = urlparse(self.plato.base_url)
      return f"{url.scheme}://browser.{url.netloc}/plato?session_id={self.session_id}"


    def start(self):
      # get a browser connection
      # then connect to server with socketio connection
      response = requests.post(
        f"{self.api_url}/start-session",
        headers={"Authorization": f"Bearer {self.plato.api_key}"},
        json={}
      )
      response.raise_for_status()
      self.session_id = response.json()["session_id"]

      print('Started Plato browser session', self.browser_url)


    def end(self):
      response = requests.post(
        f"{self.api_url}/end-session",
        headers={"Authorization": f"Bearer {self.plato.api_key}"},
        json={"session_id": self.session_id}
      )
      response.raise_for_status()
      return response.json()

    def navigate(self, url: str):
      response = requests.post(
        f"{self.base_url}/navigate",
        headers={"Authorization": f"Bearer {self.plato.api_key}"},
        json={
          "session_id": self.session_id,
          "url": url
        }
      )
      response.raise_for_status()
      return response.json()

    def click(self, description: str):
      response = requests.post(
        f"{self.api_url}/click",
        headers={"Authorization": f"Bearer {self.plato.api_key}"},
        json={
          "session_id": self.session_id,
          "description": description
        }
      )
      response.raise_for_status()
      return response.json()


    def type(self, text: str):
      response = requests.post(
        f"{self.api_url}/type",
        headers={"Authorization": f"Bearer {self.plato.api_key}"},
        json={
          "session_id": self.session_id,
          "text": text
        }
      )
      response.raise_for_status()
      return response.json()

    def extract(self, description: str, schema: ExtractParameter):
      response = requests.post(
        f"{self.base_url}/extract",
        headers={"Authorization": f"Bearer {self.plato.api_key}"},
        json={
          "session_id": self.session_id,
          "description": description,
          "schema": schema.model_dump()
        }
      )
      response.raise_for_status()
      return response.json()


    def task(self, task: str, start_url: Optional[str] = None):
      response = requests.post(
        f"{self.api_url}/task",
        headers={"Authorization": f"Bearer {self.plato.api_key}"},
        json={
          "session_id": self.session_id,
          "task": task,
          "start_url": start_url
        }
      )
      response.raise_for_status()
      return response.json()


    def monitor(self, url: str, **kwargs):
      pass

    def job(self, job_id: str, **kwargs):
      pass


  def start_session(self) -> 'PlatoSession':
    session = self.PlatoSession(self)
    session.start()
    return session

