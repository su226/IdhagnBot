from ..util import register, Animated
from PIL import Image
import os

plugin_dir = os.path.dirname(os.path.abspath(__file__))

BOXES = [
  (180, 60, 100, 100),
  (184, 75, 100, 100),
  (183, 98, 100, 100),
  (179, 118, 110, 100),
  (156, 194, 150, 48),
  (178, 136, 122, 69),
  (175, 66, 122, 85),
  (170, 42, 130, 96),
  (175, 34, 118, 95),
  (179, 35, 110, 93),
  (180, 54, 102, 93),
  (183, 58, 97, 92),
  (174, 35, 120, 94),
  (179, 35, 109, 93),
  (181, 54, 101, 92),
  (182, 59, 98, 92),
  (183, 71, 90, 96),
  (180, 131, 92, 101)
]

@register(["玩", "顶", "play"], "制作猫猫虫玩球 GIF", '''\
/玩 - 玩弄机器人（？）
/玩 <某人> - 玩弄某人（？）
可以使用头像，也可以使用图片链接''')
async def play(img: Image.Image) -> Animated:
  frames: list[Image.Image] = []
  for i in range(23):
    frames.append(Image.open(os.path.join(plugin_dir, f"{i}.png")))
  for i, (x, y, w, h) in enumerate(BOXES):
    frame = Image.new('RGBA', (480, 400), (255, 255, 255, 0))
    frame.paste(img.resize((w, h), Image.ANTIALIAS), (x, y))
    frame.paste(frames[i], mask=frames[i])
    frames[i] = frame
  result_frames: list[Image.Image] = []
  for i in range(2):
    result_frames.extend(frames[0:12])
  result_frames.extend(frames[0:8])
  result_frames.extend(frames[12:18])
  result_frames.extend(frames[18:23])
  return Animated(result_frames, 60)
