from ..util import register
from PIL import Image, ImageDraw, ImageFont
import os
import nonebot

plugin_dir = os.path.dirname(os.path.abspath(__file__))
font = ImageFont.truetype("/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc", 80)

@register(["旺仔", "旺旺", "我爱"], "制作旺旺牛奶包装盒", '''\
/旺仔 - 机器人奶（？）
/旺仔 <某人> - 某人的奶（？？）
只能使用头像''', user=True)
async def handler(user: int, avatar: Image.Image) -> Image.Image:
  username = (await nonebot.get_bot().call_api("get_stranger_info", user_id=user))["nickname"]
  im = Image.open(os.path.join(plugin_dir, "template.png"))
  w, h = font.getsize(username)
  text = Image.new("RGBA", (w, h))
  draw = ImageDraw.Draw(text)
  draw.text((0, 0), username, (255, 255, 255), font)
  if w > 355:
    text = text.resize((355, h), Image.ANTIALIAS)
  im.paste(text, (157, 51), text)
  avatar = avatar.resize((226, 226), Image.ANTIALIAS)
  im.paste(avatar, (136, 182), avatar)
  return im
