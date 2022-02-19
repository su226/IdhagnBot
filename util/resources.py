from PIL import ImageFont
from util.config import BaseConfig, BaseModel, Field
import pyppeteer

class Font(BaseModel):
  path: str
  index: int

class Config(BaseConfig):
  __file__ = "resources"
  default_font: str | Font = "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc"
  fonts: dict[str, str | Font] = Field(default_factory=dict)
  chromium: str = "/usr/bin/chromium"

CONFIG = Config.load()

def font(name: str, size: int) -> ImageFont.FreeTypeFont:
  font = CONFIG.fonts.get(name, CONFIG.default_font)
  if isinstance(font, str):
    path = font
    index = 0
  else:
    path = font.path
    index = font.index
  return ImageFont.truetype(path, size, index)

def launch_pyppeteer(**options):
  return pyppeteer.launch(options, executablePath=CONFIG.chromium)
