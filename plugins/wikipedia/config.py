from util.config import BaseConfig

class Config(BaseConfig):
  __file__ = "wikipedia"
  zim: str = ""
  page_size: int = 10
  width: int = 800
  scale: float = 1
  use_opencc: bool = True

CONFIG = Config.load()
