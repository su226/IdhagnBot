from typing import cast
from util import resources
from ..util import register
from PIL import Image, ImageDraw
from nonebot.adapters.onebot.v11 import Bot
import os
import nonebot

class GimpPerspective:
  def __init__(self, a: float, b: float, c: float, d: float, e: float, f: float, g: float, h: float):
    self.matrix = (1 / a, -b, -c, -d, 1 / e, -f, -g, -h)

  def getdata(self):
    return Image.PERSPECTIVE, self.matrix

plugin_dir = os.path.dirname(os.path.abspath(__file__))

@register(["警察", "police"], "制作狗狗警察图", '''\
/警察 - 出警
/警察 <对方> - 被出警
低调使用小心进局子
只能使用头像''', user=True, swap=True)
async def police(user: int, avatar: Image.Image) -> Image.Image:
  bot = cast(Bot, nonebot.get_bot())
  large = avatar.resize((460, 460), Image.ANTIALIAS).rotate(-17, Image.BICUBIC, True)
  pre_small = avatar.resize((118, 118), Image.ANTIALIAS)
  small = Image.new("RGBA", (120, 120))
  small.paste(pre_small, (1, 1), pre_small)
  small = small.transform((200, 200), GimpPerspective(0.9885, 0.0598, 0, 0.0453, 0.9170, 0, 0, -0.0004), resample=Image.BICUBIC)
  im = Image.new("RGB", (600, 600), (255, 255, 255))
  im.paste(large, (84, 114), large)
  template = Image.open(os.path.join(plugin_dir, "template.png"))
  im.paste(template, (0, 0), template)
  im.paste(small, (82, 409), small)
  font = resources.font("sans", 16)
  username = (await bot.get_stranger_info(user_id=user))["nickname"]
  w, _ = font.getsize(username)
  text = Image.new("RGBA", (max(120, w), 24))
  draw = ImageDraw.Draw(text)
  draw.text((text.width / 2, 12), username, (0, 0, 0), font, "mm")
  text = text.resize((120, 24), Image.ANTIALIAS).transform((123, 24), Image.AFFINE, (1, -0.125, 0, 0, 1, 0), Image.BICUBIC)
  im.paste(text, (90, 534), text)
  return im
