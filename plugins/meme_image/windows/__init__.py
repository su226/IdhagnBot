from ..util import register
from PIL import Image
import os

plugin_dir = os.path.dirname(os.path.abspath(__file__))

@register(["windows", "win10", "win"], "制作Windows 10默认壁纸探头", '''\
/劈瓜 - 机器人探头
/劈瓜 <对方> - 对方探头
可以使用头像，也可以使用图片链接''')
async def windows(self: Image.Image) -> Image.Image:
  self = self.resize((435, 435), Image.ANTIALIAS)
  im = Image.new("RGB", (666, 666), (255, 255, 255))
  im.paste(self, (123, 116), self)
  template = Image.open(os.path.join(plugin_dir, "template.png"))
  im.paste(template, mask=template)
  return im
