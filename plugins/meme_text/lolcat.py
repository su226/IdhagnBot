from io import BytesIO
from PIL import Image, ImageDraw
from util import resources
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
import math
import random
import nonebot

OMEGA = 0.2

def rainbow(x: float, phi: float) -> tuple[int, int, int]:
  r = math.sin(OMEGA * x + phi)                  * 127 + 128
  g = math.sin(OMEGA * x + phi + math.pi * 2 /3) * 127 + 128
  b = math.sin(OMEGA * x + phi + math.pi * 4 /3) * 127 + 128
  return (int(r), int(g), int(b))

lolcat = nonebot.on_command("lolcat")
lolcat.__cmd__ = "lolcat"
lolcat.__brief__ = "彩虹和独角兽！"
lolcat.__doc__ = '''\
/lolcat <文本>
灵感来自github.com/busyloop/lolcat'''
@lolcat.handle()
async def handle_lolcat(arg: Message = CommandArg()):
  text = arg.extract_plain_text().strip() or lolcat.__doc__
  font_size = 32
  font = resources.font("sans", font_size)
  w, h = font.getsize_multiline(text, spacing=0)
  _, line_height = font.getsize("A")
  h += font.getmetrics()[1]
  im = Image.new("RGB", (w + 128, h + 128), (33, 33, 33))
  draw = ImageDraw.Draw(im)
  y = 64
  rainbow_x = 0
  phi = random.uniform(0, 2 * math.pi)
  for i, line in enumerate(text.splitlines()):
    x = 64
    rainbow_x = i
    for char in line:
      cw, _ = font.getsize(char)
      draw.text((x, y), char, rainbow(rainbow_x, phi), font)
      x += cw
      rainbow_x += cw / font_size
    y += line_height
  f = BytesIO()
  im.save(f, "png")
  await lolcat.send(MessageSegment.image(f))
