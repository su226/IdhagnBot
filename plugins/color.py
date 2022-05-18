from io import BytesIO
import random

from PIL import Image, ImageDraw
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import Message, MessageSegment
import nonebot

from util import color, resources, command

color_img = (command.CommandBuilder("color", "色图", "color")
  .brief("哎哟这个色啊！好色！")
  .usage('''\
支持多种格式，比如以下均为蓝色
/色图 #0000ff
/色图 0000ff
/色图 #00f
/色图 00f
/色图 rgb(0, 0, 255)
/色图 hsl(240, 100%, 50%)
/色图 blue''')
  .build())
@color_img.handle()
async def handle_color_img(arg: Message = CommandArg()):
  color_str = arg.extract_plain_text().rstrip()
  if color_str:
    value = color.parse(color_str)
    if value is None:
      await color_img.finish(f"未知颜色：{color_str}")
  else:
    value = random.randint(0, 0xffffff)
  r, g, b = color.split_rgb(value)
  h, s, l = color.rgb2hsl(r, g, b)
  fg = (255, 255, 255) if color.luminance(r, g, b) < 0.5 else (0, 0, 0)
  im = Image.new("RGB", (1000, 1000), (r, g, b))
  draw = ImageDraw.Draw(im)
  large_font = resources.font("IBM Plex Sans", 128)
  font = resources.font("IBM Plex Sans", 64)
  lines = [
    (large_font, f"#{value:06x}"),
    (font, f"rgb({r}, {g}, {b})"),
    (font, f"hsl({h:.1f}deg, {s * 100:.1f}%, {l * 100:.1f}%)"),
  ]
  if value in color.NAMES:
    lines.append((font, color.NAMES[value]))
  y = 500 - sum(font.getsize("A")[1] + round(font.size * 0.2) for font, _ in lines) / 2
  for font, text in lines:
    w, h = font.getsize(text)
    draw.text((500 - w / 2, y), text, fg, font)
    y += h + round(font.size * 0.2)
  f = BytesIO()
  im.save(f, "png")
  await color_img.finish(MessageSegment.image(f))
