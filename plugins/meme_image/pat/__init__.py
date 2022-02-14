from ..util import register, Animated
from PIL import Image
import os

plugin_dir = os.path.dirname(os.path.abspath(__file__))

FRAME_ORDER = [0, 1, 2, 3, 1, 2, 3, 0, 1, 2, 3, 0, 0, 1, 2, 3, 0, 0, 0, 0, 4, 5, 5, 5, 6, 7, 8, 9]
BOXES = [(11, 73, 106, 100), (8, 79, 112, 96)]

@register(["拍拍", "拍", "pat"], "制作猫猫虫拍瓜 GIF 图", '''\
/拍拍 - 使用者拍机器人
/拍拍 <对方> - 使用者拍对方
/拍拍 <某人> <对方> - 某人拍对方
可以使用头像，也可以使用图片链接
~~你TM拍我瓜是吧~~''')
async def pat(self: Image.Image) -> Animated:
  frames: list[Image.Image] = []
  for i in range(10):
    frame = Image.new('RGBA', (235, 196), (255, 255, 255, 0))
    x, y, w, h = BOXES[1 if i == 2 else 0]
    frame.paste(self.resize((w, h), Image.ANTIALIAS), (x, y))
    raw_frame = Image.open(os.path.join(plugin_dir, f"{i}.png"))
    frame.paste(raw_frame, mask=raw_frame)
    frames.append(frame)
  frames = [frames[n] for n in FRAME_ORDER]
  return Animated(frames, 85)
