from ..util import register, circle, Animated
from PIL import Image
import os

plugin_dir = os.path.dirname(os.path.abspath(__file__))

OTHER_BOXES = [
  (58, 90),
  (62, 95),
  (42, 100),
  (50, 100),
  (56, 100),
  (18, 120),
  (28, 110),
  (54, 100),
  (46, 100),
  (60, 100),
  (35, 115),
  (20, 120),
  (40, 96)
]
SELF_BOXES = [
  (92, 64),
  (135, 40),
  (84, 105),
  (80, 110),
  (155, 82),
  (60, 96),
  (50, 80),
  (98, 55),
  (35, 65),
  (38, 100),
  (70, 80),
  (84, 65),
  (75, 65)
]

@register(["亲亲", "亲", "kiss"], "制作亲亲 GIF 图", '''\
/亲亲 - 使用者亲机器人
/亲亲 <对方> - 使用者亲对方
/亲亲 <某人> <对方> - 某人亲对方
可以使用头像，也可以使用图片链接''', has_self=True)
async def kiss(self: Image.Image, other: Image.Image) -> Animated:
  frames: list[Image.Image] = []
  self = circle(self).resize((40, 40), Image.ANTIALIAS)
  other = circle(other).resize((50, 50), Image.ANTIALIAS)
  for i in range(13):
    frame = Image.open(os.path.join(plugin_dir, f"{i}.png"))
    frame.paste(other, OTHER_BOXES[i], other)
    frame.paste(self, SELF_BOXES[i], self)
    frames.append(frame)
  return Animated(frames, 50)
