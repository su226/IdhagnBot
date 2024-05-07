from argparse import Namespace
from pathlib import Path
from typing import List

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageOps

from util import command, imutil, misc
from util.user_aliases import AvatarGetter, DefaultType

DIR = Path(__file__).resolve().parent
BOXES = [
  (-50, 20), (-40, 10), (-30, 0), (-20, -10), (-10, -10), (0, 0), (10, 10), (20, 20), (10, 10),
  (0, 0), (-10, -10), (10, 0), (-30, 10)]


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
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
  command.CommandBuilder("meme_pic.punch", "打拳")
  .category("meme_pic")
  .brief("现实中我唯唯诺诺，网络上我重拳出击")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, DefaultType.TARGET)

  def make() -> MessageSegment:
    target, _ = target_task.result()
    img = ImageOps.fit(target, (260, 230), imutil.scale_resample())
    frames: List[Image.Image] = []
    for i in range(13):
      frame = Image.new("RGBA", (260, 230))
      frame.paste(img, BOXES[i])
      template = Image.open(DIR / f"{i}.png")
      frame.paste(template, mask=template)
      frames.append(frame)
    return imutil.to_segment(frames, 30, afmt=args.format)

  await matcher.finish(await misc.to_thread(make))
