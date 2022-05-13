from io import BytesIO
import os
import random

from PIL import Image, ImageOps
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
import nonebot

from util import color

plugin_dir = os.path.dirname(os.path.abspath(__file__))
IMAGES = 50
DURATION = 75

cabbage = nonebot.on_command("菜狗")
cabbage.__cmd__ = "菜狗"
cabbage.__brief__ = "生成彩色菜狗GIF"
cabbage.__doc__ = '''\
/菜狗 - 生成随机颜色的菜狗
/菜狗 <颜色> - 生成指定颜色的菜狗
/菜狗 <多个颜色> - 生成渐变色的菜狗
颜色可以是16进制，也可以是CSS颜色'''
@cabbage.handle()
async def handle_cabbage(args: Message = CommandArg()):
  colors = []
  for i in args.extract_plain_text().split():
    value = color.parse(i)
    if value is None:
      await cabbage.finish(f"无效的颜色: {i}")
    colors.append(color.split_rgb(value))
  if len(colors) == 0:
    colors = [color.split_rgb(random.choice(list(color.NAMES)))]
  frames: list[Image.Image] = []
  for i in range(IMAGES):
    index, ratio = divmod(i / (IMAGES - 1) * (len(colors) - 1), 1)
    index = int(index)
    if ratio < 0.01:
      value = colors[index]
    else:
      value = color.blend(colors[index + 1], colors[index], ratio)
    im = Image.open(os.path.join(plugin_dir, f"{i}.png"))
    im = ImageOps.colorize(im, (0, 0, 0), (255, 255, 255), value)
    frames.append(im)
  f = BytesIO()
  frames[0].save(f, "gif", append_images=frames[1:], save_all=True, duration=DURATION, loop=0)
  await cabbage.send(MessageSegment.image(f))
