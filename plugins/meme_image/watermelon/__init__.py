from ..util import register
from PIL import Image
import os

plugin_dir = os.path.dirname(os.path.abspath(__file__))

@register(["劈瓜", "watermelon", "刘华强", "华强"], "制作刘华强劈瓜图", '''\
/劈瓜 - 劈机器人
/劈瓜 <对方> - 劈对方
可以使用头像，也可以使用图片链接''')
async def watermelon(self: Image.Image) -> Image.Image:
  self = self.resize((548, 548), Image.ANTIALIAS)
  im = Image.new("RGB", (1440, 782), (255, 255, 255))
  im.paste(self, (401, 183), self)
  template = Image.open(os.path.join(plugin_dir, "template.png"))
  im.paste(template, mask=template)
  return im
