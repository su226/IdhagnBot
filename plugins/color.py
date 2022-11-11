import asyncio
import random

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image

from util import colorutil, command, imutil, textutil

color_img = (
  command.CommandBuilder("color", "色图", "color")
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
  .build()
)
@color_img.handle()
async def handle_color_img(arg: Message = CommandArg()):
  color_str = arg.extract_plain_text().rstrip()
  if color_str:
    value = colorutil.parse(color_str)
    if value is None:
      await color_img.finish(f"未知颜色：{color_str}")
  else:
    value = random.randint(0, 0xffffff)
  r, g, b = colorutil.split_rgb(value)
  h, s, l = colorutil.rgb2hsl(r, g, b)

  def make() -> MessageSegment:
    im = Image.new("RGB", (1000, 1000), (r, g, b))
    markup = f'''\
<span size="200%">#{value:06x}</span>
rgb({r}, {g}, {b})
hsl({h:.1f}deg, {s * 100:.1f}%, {l * 100:.1f}%)'''
    if value in colorutil.NAMES:
      markup += "\n" + colorutil.NAMES[value]
    fg = (255, 255, 255) if colorutil.luminance(r, g, b) < 0.5 else (0, 0, 0)
    textutil.paste(
      im, (im.width // 2, im.height // 2), markup, "sans", 64,
      markup=True, align="m", anchor="mm", color=fg
    )
    return imutil.to_segment(im)

  await color_img.finish(await asyncio.to_thread(make))
