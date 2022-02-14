from ..util import register, circle, Animated
from PIL import Image
import os

plugin_dir = os.path.dirname(os.path.abspath(__file__))

OTHER_BOXES = [
  (39, 91, 75, 75),
  (49, 101, 75, 75),
  (67, 98, 75, 75),
  (55, 86, 75, 75),
  (61, 109, 75, 75),
  (65, 101, 75, 75)
]
SELF_BOXES = [
  (102, 95, 70, 80, 0),
  (108, 60, 50, 100, 0),
  (97, 18, 65, 95, 0),
  (65, 5, 75, 75, -20),
  (95, 57, 100, 55, -70),
  (109, 107, 65, 75, 0)
]

@register(["贴贴", "贴"], "制作贴贴 GIF 图", '''\
/贴贴 - 使用者与机器人贴贴
/贴贴 <对方> - 使用者与对方贴贴
/贴贴 <某人> <对方> - 某人与对方贴贴
可以使用头像，也可以使用图片链接''', has_self=True)
async def make(self: Image.Image, other: Image.Image) -> Animated:
  self = circle(self)
  other = circle(other)
  frames: list[Image.Image] = []
  for i in range(6):
    frame = Image.open(os.path.join(plugin_dir, f"{i}.png"))
    x, y, w, h = OTHER_BOXES[i]
    other_head = other.resize((w, h), Image.ANTIALIAS)
    frame.paste(other_head, (x, y), mask=other_head)
    x, y, w, h, angle = SELF_BOXES[i]
    self_head = self.resize((w, h), Image.ANTIALIAS).rotate(angle, Image.BICUBIC, True)
    frame.paste(self_head, (x, y), mask=self_head)
    frames.append(frame)
  return Animated(frames, 50)
