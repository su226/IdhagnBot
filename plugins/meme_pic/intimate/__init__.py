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
  (39, 91, 75, 75), (49, 101, 75, 75), (67, 98, 75, 75), (55, 86, 75, 75), (61, 109, 75, 75),
  (65, 101, 75, 75)
]
SOURCE_BOXES = [
  (102, 95, 70, 80, 0), (108, 60, 50, 100, 0), (97, 18, 65, 95, 0), (65, 5, 75, 75, -20),
  (95, 57, 100, 55, -70), (109, 107, 65, 75, 0)
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
  command.CommandBuilder("meme_pic.intimate", "贴贴")
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
    for i in range(6):
      frame = Image.open(DIR / f"{i}.png").convert("RGB")
      x, y, w, h = TARGET_BOXES[i]
      target_1 = target.resize((w, h), imutil.scale_resample())
      frame.paste(target_1, (x, y), mask=target_1)
      x, y, w, h, angle = SOURCE_BOXES[i]
      source_1 = source.resize((w, h), imutil.scale_resample())
      source_1 = source_1.rotate(angle, imutil.resample(), True)
      frame.paste(source_1, (x, y), mask=source_1)
      frames.append(frame)
    return imutil.to_segment(frames, 50, afmt=args.format)

  await matcher.finish(await misc.to_thread(make))
