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
TARGET_BOXES = [
  (58, 90), (62, 95), (42, 100), (50, 100), (56, 100), (18, 120), (28, 110), (54, 100), (46, 100),
  (60, 100), (35, 115), (20, 120), (40, 96)
]
SOURCE_BOXES = [
  (92, 64), (135, 40), (84, 105), (80, 110), (155, 82), (60, 96), (50, 80), (98, 55), (35, 65),
  (38, 100), (70, 80), (84, 65), (75, 65)
]


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
parser.add_argument("--source", "-s", default="", metavar="源", help="同上")
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
  command.CommandBuilder("meme_pic.kiss", "亲亲", "亲", "kiss")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, event.self_id, "目标")
    source_task = g(args.source, event.user_id, "源")

  def make() -> MessageSegment:
    target, _ = target_task.result()
    source, _ = source_task.result()
    imutil.circle(target)
    imutil.circle(source)
    frames: List[Image.Image] = []
    target = target.resize((50, 50), imutil.scale_resample())
    source = source.resize((40, 40), imutil.scale_resample())
    for i in range(13):
      frame = Image.open(DIR / f"{i}.png")
      frame.paste(target, TARGET_BOXES[i], target)
      frame.paste(source, SOURCE_BOXES[i], source)
      frames.append(frame)
    return imutil.to_segment(frames, 50, afmt=args.format)

  await matcher.finish(await misc.to_thread(make))
