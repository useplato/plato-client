
BASE_URL = "https://api.plato.so"

class PlatoSession:
  def __init__(self, session_id: str):
    self.session_id = session_id

  def act(self, action: str, **kwargs):
    pass

  def extract(self, url: str, **kwargs):
    pass

  def monitor(self, url: str, **kwargs):
    pass

  def job(self, job_id: str, **kwargs):
    pass



class PlatoClient:
  @staticmethod
  def start_session() -> PlatoSession:
    pass
