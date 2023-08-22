from argparse import Namespace
from typing import List

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, imutil, misc, textutil
from util.user_aliases import AvatarGetter, DefaultType

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
  command.CommandBuilder("meme_pic.keep", "一直")
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
    text1 = textutil.render("要我一直", "sans", 60)
    text2 = textutil.render("吗", "sans", 60)

    frames: List[Image.Image] = []
    for raw in imutil.frames(target):
      raw = raw.convert("RGBA")
      big = imutil.resize_width(raw, 500)
      small = imutil.resize_width(raw, 100)
      text_h = max(small.height, text1.height, text2.height)
      im = Image.new("RGB", (big.width, big.height + text_h), (255, 255, 255))
      im.paste(big, mask=big)
      x = (im.width - small.width - text1.width - text2.width) // 2
      y = big.height + text_h // 2
      im.paste(text1, (x, y - text1.height // 2), text1)
      x += text1.width
      im.paste(small, (x, y - small.height // 2), small)
      x += small.width
      im.paste(text2, (x, y - text2.height // 2), text2)
      frames.append(im)

    return imutil.to_segment(frames, target, afmt=args.format)

  await matcher.finish(await misc.to_thread(make))
