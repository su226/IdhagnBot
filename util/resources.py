import pyppeteer
from PIL import ImageFont
from PIL import features as PILFeatures
from pydantic import BaseModel, Field

from util.config import BaseConfig

__all__ = ["font", "launch_pyppeteer"]


class Font(BaseModel):
  path: str
  index: int


class Config(BaseConfig, file="resources"):
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
  if PILFeatures.check("raqm"):
    engine = ImageFont.LAYOUT_RAQM
  else:
    engine = ImageFont.LAYOUT_BASIC
  return ImageFont.truetype(path, size, index, layout_engine=engine)


def launch_pyppeteer(**options):
  return pyppeteer.launch(options, executablePath=CONFIG.chromium)
