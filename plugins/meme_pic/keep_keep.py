from argparse import Namespace
from typing import List

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, imutil, misc, textutil
from util.user_aliases import AvatarGetter, DefaultType

FRAMETIME = 100


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接（可传入动图）"
))
group = parser.add_mutually_exclusive_group()
group.add_argument(
  "--webp", "-w", action="store_const", dest="format", const="webp", default="gif",
  help="使用WebP而非GIF格式"
)
group.add_argument(
  "--png", "--apng", "-p", action="store_const", dest="format", const="png",
  help="使用APNG而非GIF格式"
)
matcher = (
  command.CommandBuilder("meme_pic.keep_keep", "一直一直")
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
    small_h = target.height * 125 // target.width
    text_h = max(small_h, text1.height, text2.height)

    base_scale = 5 ** (1 / 20)

    frames: List[Image.Image] = []
    for i, raw in zip(range(20), imutil.sample_frames(target, FRAMETIME)):
      raw = raw.convert("RGBA")
      big = imutil.resize_width(raw, 500)
      im_one = Image.new("RGB", (500, big.height + text_h), "white")
      x = (im_one.width - 100 - text1.width - text2.width) // 2
      y = big.height + text_h // 2
      im_one.paste(text1, (x, y - text1.height // 2), text1)
      x += text1.width + 100
      im_one.paste(text2, (x, y - text2.height // 2), text2)
      im_one.paste(big, mask=big)
      im = Image.new("RGB", im_one.size, (255, 255, 255))
      scale = base_scale ** i
      for _ in range(4):
        x = int(358 * (1 - scale))
        y = int(im.height * (1 - scale))
        w = int(500 * scale)
        h = int(im.height * scale)
        im.paste(im_one.resize((w, h)), (x, y))
        scale /= 5
      frames.append(im)

    return imutil.to_segment(frames, FRAMETIME, afmt=args.format)

  await matcher.finish(await misc.to_thread(make))
