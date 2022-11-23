import random
from pathlib import Path
from typing import List

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image, ImageOps

from util import colorutil, command, imutil, misc

DIR = Path(__file__).resolve().parent
IMAGES = 50
DURATION = 75

cabbage = (
  command.CommandBuilder("cabbage_doge", "菜狗")
  .brief("生成彩色菜狗GIF")
  .usage('''\
/菜狗 - 生成随机颜色的菜狗
/菜狗 <颜色> - 生成指定颜色的菜狗
/菜狗 <多个颜色> - 生成渐变色的菜狗
颜色可以是16进制，也可以是CSS颜色''')
  .build()
)
@cabbage.handle()
async def handle_cabbage(args: Message = CommandArg()):
  colors = []
  for i in args.extract_plain_text().split():
    value = colorutil.parse(i)
    if value is None:
      await cabbage.finish(f"无效的颜色: {i}")
    colors.append(colorutil.split_rgb(value))
  if len(colors) == 0:
    colors = [colorutil.split_rgb(random.choice(list(colorutil.NAMES)))]

  def make() -> MessageSegment:
    frames: List[Image.Image] = []
    for i in range(IMAGES):
      index, ratio = divmod(i / (IMAGES - 1) * (len(colors) - 1), 1)
      index = int(index)
      if ratio < 0.01:
        value = colors[index]
      else:
        value = colorutil.blend(colors[index + 1], colors[index], ratio)
      im = Image.open(DIR / f"{i}.png")
      im = ImageOps.colorize(im, (0, 0, 0), (255, 255, 255), value)  # type: ignore
      frames.append(im)
    return imutil.to_segment(frames, DURATION)

  await cabbage.finish(await misc.to_thread(make))
