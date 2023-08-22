from argparse import Namespace
from pathlib import Path
from typing import List

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageEnhance, ImageFilter

from util import command, imutil, misc, textutil
from util.user_aliases import AvatarGetter, DefaultType

DIR = Path(__file__).resolve().parent


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接（可传入动图）"
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
matcher = (
  command.CommandBuilder("meme_pic.loading", "加载中")
  .category("meme_pic")
  .brief("[动]")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, DefaultType.TARGET, raw=True)

  def make() -> MessageSegment:
    target, _ = target_task.result()
    big = imutil.resize_width(target.convert("RGBA"), 500)
    mask = Image.new("RGB", big.size, (255, 255, 255))
    mask.paste(big, mask=big)
    mask = ImageEnhance.Brightness(mask).enhance(0.5)
    mask = mask.filter(ImageFilter.GaussianBlur(3))
    icon = Image.open(DIR / "icon.png")
    imutil.paste(mask, icon, (big.width // 2, big.height // 2), anchor="mm")
    text1 = textutil.render("不出来", "sans", 60)

    frames: List[Image.Image] = []
    for raw in imutil.frames(target):
      small = imutil.resize_width(raw.convert("RGBA"), 100)
      text_h = max(small.height, text1.height)
      im = Image.new("RGB", (big.width, big.height + text_h), (255, 255, 255))
      im.paste(mask)
      x = (im.width - small.width - text1.width) // 2
      y = big.height + text_h // 2
      im.paste(small, (x, y - small.height // 2), small)
      x += small.width
      im.paste(text1, (x, y - text1.height // 2), text1)
      frames.append(im)

    return imutil.to_segment(frames, target, afmt=args.format)

  await matcher.finish(await misc.to_thread(make))
