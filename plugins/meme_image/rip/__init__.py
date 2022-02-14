from ..util import register
from PIL import Image
import os

plugin_dir = os.path.dirname(os.path.abspath(__file__))

FRAME_ORDER = [0, 1, 2, 3, 1, 2, 3, 0, 1, 2, 3, 0, 0, 1, 2, 3, 0, 0, 0, 0, 4, 5, 5, 5, 6, 7, 8, 9]
BOXES = [(11, 73, 106, 100), (8, 79, 112, 96)]

@register(["撕"], "制作熊猫头撕头像图", '''\
/撕 - 撕机器人
/撕 <对方> - 撕对方
可以使用头像，也可以使用图片链接''')
async def rip(self: Image.Image) -> Image.Image:
  self = self.resize((385, 385), Image.ANTIALIAS)
  template = Image.open(os.path.join(plugin_dir, "template.png"))
  im = Image.new('RGBA', template.size, (255, 255, 255, 0))
  im.paste(self.rotate(24, Image.BICUBIC, True), (-5, 355))
  im.paste(self.rotate(-11, Image.BICUBIC, True), (649, 310))
  im.paste(template, mask=template)
  return im
