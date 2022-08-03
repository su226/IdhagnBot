import random
from io import BytesIO

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image

from util import color, command, text

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
  im = Image.new("RGB", (1000, 1000), (r, g, b))

  markup = f'''\
<span size="200%">#{value:06x}</span>
rgb({r}, {g}, {b})
hsl({h:.1f}deg, {s * 100:.1f}%, {l * 100:.1f}%)'''
  if value in color.NAMES:
    markup += "\n" + color.NAMES[value]
  fg = (255, 255, 255) if color.luminance(r, g, b) < 0.5 else (0, 0, 0)
  text.paste(
    im, (im.width // 2, im.height // 2), markup, "sans", 64,
    markup=True, align="m", anchor="mm", color=fg)

  f = BytesIO()
  im.save(f, "png")
  await color_img.finish(MessageSegment.image(f))
