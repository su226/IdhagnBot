from argparse import Namespace
from io import BytesIO
from typing import List

import numpy as np
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ImageOps

from util import command, context, imutil, misc, textutil
from util.misc import range_float, range_int
from util.user_aliases import AvatarGetter, DefaultType


def apply_yuv_loss(im: Image.Image, purple: bool = False) -> Image.Image:
  if purple:
    im = ImageChops.invert(im)
  r, g, b = im.split()
  r = np.array(r).astype(np.int32)
  g = np.array(g).astype(np.int32)
  b = np.array(b).astype(np.int32)
  y = ((77 * r + 150 * g + 29 * b) >> 8).clip(0, 255)
  u = (((-43 * r - 85 * g + 128 * b) >> 8) - 1).clip(-128, 127)
  v = (((128 * r - 107 * g - 21 * b) >> 8) - 1).clip(-128, 127)
  r = ((65536 * y + 91881 * v) >> 16).clip(0, 255).astype(np.uint8)
  g = ((65536 * y - 22553 * u - 46802 * v) >> 16).clip(0, 255).astype(np.uint8)
  b = ((65536 * y + 116130 * u) >> 16).clip(0, 255).astype(np.uint8)
  r = Image.fromarray(r, "L")
  g = Image.fromarray(g, "L")
  b = Image.fromarray(b, "L")
  im = Image.merge("RGB", (r, g, b))
  if purple:
    im = ImageChops.invert(im)
  return im


def apply_watermark(watermarks: List[str], rand: np.random.Generator, im: Image.Image) -> None:
  name = rand.choice(watermarks)
  pos = rand.integers(0, 3)
  short = min(im.width, im.height)
  size = rand.integers(int(0.035 * short), int(0.045 * short))
  text_im = textutil.render("@" + name, "sans", size, color=(255, 255, 255))
  blur = int(0.15 * size)
  shadow_im = ImageOps.expand(text_im.getchannel("A"), blur)
  shadow_im = ImageEnhance.Brightness(shadow_im).enhance(0.6)
  shadow_im = shadow_im.filter(ImageFilter.BoxBlur(blur))
  if pos == 0:  # 中
    x = (im.width - text_im.width) // 2
    y = (im.height - text_im.height) // 2
  elif pos == 1:  # 中下
    x = (im.width - text_im.width) // 2
    y = im.height - text_im.height - size // 2
  else:  # 右下
    x = im.width - text_im.width - size // 2
    y = im.height - text_im.height - size // 2
  offset = int(0.4 * size)
  x += rand.integers(-offset, offset)
  y += rand.integers(-offset, offset)
  shadow_offset = int(0.04 * size)
  im.paste((0, 0, 0), (x - blur, y - blur + shadow_offset), shadow_im)
  im.paste(text_im, (x, y), text_im)


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接（可传入动图）"
))
parser.add_argument(
  "--yuv-loss", "-y", choices=["none", "green", "purple"], default="green",
  help="YUV精度损失，可用: none (无)、green (发绿)、purple (发紫)，默认: green"
)
parser.add_argument("--repeat", "-r", type=range_int(1, 20), default=12, metavar="次数", help=(
  "做旧次数，为 [1, 20] 之间的整数，默认: 12"
))
parser.add_argument("--blur", "-b", type=range_float(0, 100), default=0, metavar="强度", help=(
  "模糊强度，为 [0, 100] 之间的小数，默认: 0"
))
parser.add_argument("--quality", "-q", type=range_int(0, 101), default=60, metavar="质量", help=(
  "JPEG压缩质量，为[0, 101] 之间的整数，101为不压缩，默认: 60"
))
parser.add_argument("--noise", "-n", type=range_int(0, 127), default=0, metavar="强度", help=(
  "噪点强度，为[0, 127] 之间的整数，默认: 0"
))
parser.add_argument("--no-member-name", "-M", action="store_false", dest="member_name", help=(
  "不使用群员的名字作为水印"
))
parser.add_argument("--watermark", "-a", action="append", default=[], metavar="内容", help=(
  "自定义水印，可以指定多次，你可能需要配合 --no-member-name 使用"
))
parser.add_argument("--offset", "-o", type=range_float(0, 100), default=0.5, metavar="比率", help=(
  "随机偏移百分比，默认: 0.5"
))
group = parser.add_mutually_exclusive_group()
group.add_argument(
  "--webp", "-w", action="store_const", dest="format", const="webp", default="gif",
  help="使用WebP而非GIF格式（如果传入动图）"
)
group.add_argument(
  "--png", "--apng", "-p", action="store_const", dest="format", const="png",
  help="使用APNG而非GIF格式（如果传入动图）"
)
parser.epilog = "特别感谢: https://magiconch.com/patina/"
matcher = (
  command.CommandBuilder(
    "meme_pic.patina", "电子包浆", "赛博包浆", "电子做旧", "赛博做旧", "包浆", "做旧"
  )
  .category("meme_pic")
  .brief("[动]")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, DefaultType.TARGET, raw=True)
  watermarks = args.watermark.copy()
  ctx = context.get_event_context(event)
  if args.member_name and ctx != -1:
    members = await bot.get_group_member_list(group_id=ctx)
    watermarks.extend(i["card"] or i["nickname"] for i in members)

  def make() -> MessageSegment:
    target, _ = target_task.result()
    size = min(target.width, target.height)
    offset = int(args.offset / 100 * size)
    blur = args.blur / 100 * size

    seed = np.random.SeedSequence()
    frames: List[Image.Image] = []
    for raw in imutil.frames(target):
      rand = np.random.default_rng(seed)
      im = raw.convert("RGB")
      if blur:
        im = im.filter(ImageFilter.BoxBlur(blur))
      if (n := args.noise):
        arr = rand.integers(128 - n, 128 + n, (500, 500, 3), np.uint8)
        noise = Image.fromarray(arr).resize(im.size, Image.Resampling.BILINEAR)
        im = ImageChops.add(im, noise, offset=-128)
      for _ in range(args.repeat):
        if watermarks:
          apply_watermark(watermarks, rand, im)
        if (y := args.yuv_loss):
          im = apply_yuv_loss(im, y == "purple")
        if offset:
          x = rand.integers(-offset, offset)
          y = rand.integers(-offset, offset)
          im2 = im.copy()
          im = im.resize((im.width + x, im.height + y), Image.Resampling.BILINEAR)
          im2.paste(im, ((im2.width - im.width) // 2, (im2.height - im.height) // 2))
          im = im2
        if (q := args.quality) != 101:
          f = BytesIO()
          q = int(q + rand.integers(10))
          im.save(f, "JPEG", quality=q)
          im = Image.open(f)
      frames.append(im)

    return imutil.to_segment(frames, target, afmt=args.format)

  await matcher.finish(await misc.to_thread(make))
