from ..util import register
from PIL import Image
import os
import random

plugin_dir = os.path.dirname(os.path.abspath(__file__))

FRAME_ORDER = [0, 1, 2, 3, 1, 2, 3, 0, 1, 2, 3, 0, 0, 1, 2, 3, 0, 0, 0, 0, 4, 5, 5, 5, 6, 7, 8, 9]
BOXES = [(11, 73, 106, 100), (8, 79, 112, 96)]

@register(["cxk", "蔡徐坤", "篮球", "jntm", "鸡你太美"], "制作蔡徐坤打篮球图", '''\
/cxk - 使用者打机器人
/cxk <对方> - 使用者打对方
/cxk <某人> <对方> - 某人打对方
可以使用头像，也可以使用图片链接''', has_self=True)
async def rip(self: Image.Image, other: Image.Image) -> Image.Image:
  self = self.resize((130, 130), Image.ANTIALIAS)
  other = other.resize((130, 130), Image.ANTIALIAS).rotate(random.uniform(0, 360), Image.BICUBIC)
  im = Image.new("RGB", (830, 830), (255, 255, 255))
  im.paste(self, (382, 59), self)
  im.paste(other, (609, 317), other)
  template = Image.open(os.path.join(plugin_dir, "template.png"))
  im.paste(template, mask=template)
  return im
