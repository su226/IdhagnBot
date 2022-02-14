from ..util import register
from PIL import Image
import os

plugin_dir = os.path.dirname(os.path.abspath(__file__))

FRAME_ORDER = [0, 1, 2, 3, 1, 2, 3, 0, 1, 2, 3, 0, 0, 1, 2, 3, 0, 0, 0, 0, 4, 5, 5, 5, 6, 7, 8, 9]
BOXES = [(11, 73, 106, 100), (8, 79, 112, 96)]

@register("protogen", "制作Protogen扫二维码图", '''\
/protogen - 扫机器人
/protogen <对方> - 扫对方
可以使用头像，也可以使用图片链接''')
async def protogen(self: Image.Image) -> Image.Image:
  self = self.resize((200, 200), Image.ANTIALIAS)
  im = Image.new("RGB", (960, 888), (255, 255, 255))
  im.paste(self, (215, 604), self)
  template = Image.open(os.path.join(plugin_dir, "template.png"))
  im.paste(template, mask=template)
  return im
