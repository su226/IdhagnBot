from ..util import register, circle
from PIL import Image
import os
import random

plugin_dir = os.path.dirname(os.path.abspath(__file__))

@register(["扔", "throw"], "制作古明地觉扔头像图", '''\
/拍拍 - 撕机器人
/拍拍 <对方> - 撕对方
可以使用头像，也可以使用图片链接''')
async def rip(self: Image.Image) -> Image.Image:
  self = circle(self.resize((143, 143), Image.ANTIALIAS)).rotate(random.randint(1, 360), Image.BICUBIC, expand=False)
  im = Image.open(os.path.join(plugin_dir, "template.png"))
  im.paste(self, (15, 178), mask=self)
  return im
