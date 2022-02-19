from util.config import BaseConfig

class Config(BaseConfig):
  __file__ = "meme_text"
  chrome: str = "/usr/bin/chromium"

CONFIG = Config.load()
