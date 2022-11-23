from argparse import Namespace
from pathlib import Path
from typing import List

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, imutil, misc
from util.user_aliases import AvatarGetter

DIR = Path(__file__).resolve().parent
BOXES = [
  (14, 20, 98, 98), (12, 33, 101, 85), (8, 40, 110, 76), (10, 33, 102, 84), (12, 20, 98, 98)
]


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
parser.add_argument("--circle", "-c", action="store_true", help="让头像变圆")
group = parser.add_mutually_exclusive_group()
group.add_argument(
  "--webp", action="store_const", dest="format", const="webp", default="gif",
  help="使用WebP而非GIF格式"
)
group.add_argument(
  "--png", "--apng", "-p", action="store_const", dest="format", const="png",
  help="使用APNG而非GIF格式"
)
matcher = (
  command.CommandBuilder("meme_pic.petpet", "petpet", "pet", "rua", "摸头")
  .brief("rua~")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, event.self_id)

  def make() -> MessageSegment:
    target, _ = target_task.result()
    frames: List[Image.Image] = []
    for i in range(5):
      frame = Image.new("RGBA", (112, 112))
      x, y, w, h = BOXES[i]
      target1 = target.resize((w, h), imutil.scale_resample())
      if args.circle:
        imutil.circle(target1, args.format != "gif")
      frame.paste(target1, (x, y), target1)
      hand = Image.open(DIR / f"{i}.png").convert("RGBA")
      frame.paste(hand, mask=hand)
      frames.append(frame)
    return imutil.to_segment(frames, 60, afmt=args.format)

  await matcher.finish(await misc.to_thread(make))
