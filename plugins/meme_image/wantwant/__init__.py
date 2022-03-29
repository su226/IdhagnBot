from typing import cast
from ..util import register
from util import resources
from PIL import Image, ImageDraw
from nonebot.adapters.onebot.v11 import Bot
import os
import nonebot

plugin_dir = os.path.dirname(os.path.abspath(__file__))

@register(["旺仔", "旺旺", "我爱"], "制作旺旺牛奶包装盒", '''\
/旺仔 - 机器人奶（？）
/旺仔 <某人> - 某人的奶（？？）
只能使用头像''', user=True)
async def handler(user: int, avatar: Image.Image) -> Image.Image:
  bot = cast(Bot, nonebot.get_bot())
  username = (await bot.get_stranger_info(user_id=user))["nickname"]
  im = Image.open(os.path.join(plugin_dir, "template.png"))
  font = resources.font("cute", 80)
  w, h = font.getsize(username)
  h += font.getmetrics()[1]
  text = Image.new("RGBA", (w, h))
  draw = ImageDraw.Draw(text)
  draw.text((0, 0), username, (255, 255, 255), font)
  if w > 355:
    text = text.resize((355, h), Image.ANTIALIAS)
  im.paste(text, (157, 51), text)
  avatar = avatar.resize((226, 226), Image.ANTIALIAS)
  im.paste(avatar, (136, 182), avatar)
  return im
