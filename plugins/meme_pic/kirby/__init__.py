from argparse import Namespace
from pathlib import Path
from typing import List

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, imutil, misc
from util.user_aliases import AvatarGetter, DefaultType

DIR = Path(__file__).resolve().parent
BOXES = [
  (358, 163), (359, 173), (360, 183), (357, 193), (352, 199), (337, 212), (329, 218), (320, 224),
  (318, 223), (318, 220), (320, 215), (320, 213), (320, 210), (320, 206), (320, 201), (320, 192),
  (320, 188), (320, 184), (320, 179),
]
DURATION = 50


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
parser.add_argument("--circle", "-c", action="store_true", help="让头像变圆")
group = parser.add_mutually_exclusive_group()
group.add_argument(
  "--webp", "-w", action="store_const", dest="format", const="webp", default="gif",
  help="使用WebP而非GIF格式",
)
group.add_argument(
  "--png", "--apng", "-p", action="store_const", dest="format", const="png",
  help="使用APNG而非GIF格式",
)
matcher = (
  command.CommandBuilder("meme_pic.kirby", "卡比")
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
    frames: List[Image.Image] = []

    for i, raw in zip(range(62), imutil.sample_frames(target, 50)):
      img = raw.convert("RGBA")
      img = imutil.resize_height(img, 80)
      if args.circle:
        imutil.circle(img)
      frame = Image.open(DIR / f"{i}.png")
      if i <= 18:
        imutil.paste(frame, img, BOXES[i], anchor="mt")
      elif i <= 39:
        imutil.paste(frame, img, BOXES[18], anchor="mt")
      frames.append(frame)

    return imutil.to_segment(frames, 50, afmt=args.format)

  await matcher.finish(await misc.to_thread(make))
