from ..util import register, Animated
from PIL import Image
import os

plugin_dir = os.path.dirname(os.path.abspath(__file__))

@register(["petpet", "pet", "rua"], "制作petpet GIF 图", '''\
/petpet - rua机器人
/petpet <对方> - rua对方
可以使用头像，也可以使用图片链接''')
async def rua(avatar: Image.Image) -> Animated:
  frames: list[Image.Image] = []
  locs = [
    (14, 20, 98, 98),
    (12, 33, 101, 85),
    (8, 40, 110, 76),
    (10, 33, 102, 84),
    (12, 20, 98, 98)
  ]
  for i in range(5):
    frame = Image.new('RGBA', (112, 112), (255, 255, 255, 0))
    x, y, w, h = locs[i]
    frame.paste(avatar.resize((w, h), Image.ANTIALIAS), (x, y))
    hand = Image.open(os.path.join(plugin_dir, f"{i}.png"))
    frame.paste(hand, mask=hand)
    frames.append(frame)
  return Animated(frames, 60)
