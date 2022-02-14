from typing import TypeVar
from ..util import register, circle, Animated
from PIL import Image, ImageDraw, ImageFilter
import os

AVATAR_BOX = (0, 0, 360, 360)
PRICE_BOX = (225, 66, 305, 146)
SLIDE_FRAMES = 3
AVATAR_FRAMES = 3
SCALE_FRAMES = 3
PRICE_FRAMES = 5

TBox = TypeVar("TBox", bound=tuple[int, ...])
def lerp(box1: TBox, box2: TBox, r2: float) -> TBox:
  r1 = 1 - r2
  return tuple(map(lambda i: int(i[0] * r1 + i[1] * r2), zip(box1, box2)))

def circle(img: Image.Image) -> Image.Image:
  mask = Image.new('L', img.size, 0)
  ImageDraw.Draw(mask).ellipse((1, 1, img.size[0] - 2, img.size[1] - 2), 255)
  mask = mask.filter(ImageFilter.GaussianBlur(0))
  img.putalpha(mask)
  return img

def paste(im: Image.Image, im2: Image.Image, box: tuple[int, int, int, int]):
  im2 = im2.resize((box[2] - box[0], box[3] - box[1]), Image.ANTIALIAS)
  im.paste(im2, box, im2)

plugin_dir = os.path.dirname(os.path.abspath(__file__))

@register(["indihome", "印尼宽带", "印尼", "宽带"], "制作印尼宽带推销员图", '''\
/indihome - 机器人推销宽带
/indihome <对方> - 对方推销宽带
可以使用头像，也可以使用图片链接''')
async def indihome(self: Image.Image) -> Animated:
  self = circle(self).resize((360, 360), Image.ANTIALIAS)
  frames: list[Image.Image] = []
  for i in range(SLIDE_FRAMES):
    im = Image.new("RGB", (360, 360), (255, 255, 255))
    im.paste(self, lerp((360, 0), (0, 0), i / SLIDE_FRAMES), self)
    frames.append(im)
  avatar_im = Image.new("RGBA", (360, 360), (255, 255, 255, 255))
  avatar_im.paste(self, AVATAR_BOX, self)
  for i in range(AVATAR_FRAMES):
    frames.append(avatar_im)
  price_im = Image.open(os.path.join(plugin_dir, "template.png"))
  white = Image.new("RGB", (360, 360), (255, 255, 255))
  for i in range(SCALE_FRAMES):
    ratio = (i + 1) / (SCALE_FRAMES + 1)
    im = Image.blend(white, price_im, ratio)
    paste(im, self, lerp(AVATAR_BOX, PRICE_BOX, ratio))
    frames.append(im)
  paste(price_im, self, PRICE_BOX)
  for i in range(PRICE_FRAMES):
    frames.append(price_im)
  return Animated(frames, 50)
