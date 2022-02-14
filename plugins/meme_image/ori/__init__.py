from ..util import register, circle
from PIL import Image
import os

plugin_dir = os.path.dirname(os.path.abspath(__file__))

@register(["ori", "拥抱光明", "奥日", "奥里"], "制作Ori拥抱光明图", '''\
/ori - 机器人拥抱光明
/ori <对方> - 对方拥抱光明
可以使用头像，也可以使用图片链接''')
async def ori(self: Image.Image) -> Image.Image:
  self = circle(self).resize((100, 100), Image.ANTIALIAS)
  im = Image.open(os.path.join(plugin_dir, "template.png"))
  im.paste(self, (305, 222), self)
  return im
