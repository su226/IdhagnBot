from argparse import Namespace
from pathlib import Path
from typing import Dict, List

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, imutil, misc
from util.user_aliases import AvatarGetter, DefaultType

DIR = Path(__file__).resolve().parent
BOXES = [
  (81, 56, 101), (82, 56, 102), (81, 56, 101), (81, 56, 102), (82, 56, 101), (81, 56, 102),
  (82, 56, 101), (81, 56, 102), (81, 56, 101), (81, 55, 102), (81, 56, 101), (82, 56, 102),
  (81, 56, 101), (81, 56, 102), (82, 56, 101), (81, 56, 102), (82, 56, 101), (81, 56, 102),
  (81, 56, 101), (81, 56, 102), (81, 56, 101), (81, 55, 102), (81, 56, 101), (82, 56, 102),
  (73, 50, 105), (-69, 40, 185), (-148, 69, 185),
]
FRAMES = [
  (0, 2), (1, 2), (2, 2), (3, 2), (4, 2), (5, 2), (6, 2), (5, 2), (6, 2), (7, 2), (8, 2), (9, 2),
  (10, 2), (11, 2), (12, 2), (13, 2), (14, 2), (15, 2), (16, 2), (17, 2), (18, 2), (19, 1),
  (20, 1), (21, 1), (22, 1), (23, 2), (24, 2), (25, 2), (26, 2), (27, 2), (28, 2), (29, 2),
  (30, 2), (31, 2),
]
DURATION = 50


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
  command.CommandBuilder("meme_pic.tomb", "诈尸")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, DefaultType.TARGET)

  def make() -> MessageSegment:
    target, _ = target_task.result()
    cache: Dict[int, Image.Image] = {}
    target = target.resize((215, 215), imutil.scale_resample())
    frames: List[Image.Image] = []
    for i in range(32):
      template = Image.open(DIR / f"{i}.png")
      if i < len(BOXES):
        x, y, size = BOXES[i]
        if size not in cache:
          cache[size] = target.resize((size, size), imutil.scale_resample())
        im = Image.new("RGB", template.size, (255, 255, 255))
        im.paste(cache[size], (x, y), cache[size])
        im.paste(template, mask=template)
      else:
        im = template
      frames.append(im)

    result_frames: List[Image.Image] = []
    durations: List[int] = []
    for frame, mul in FRAMES:
      result_frames.append(frames[frame])
      durations.append(mul * DURATION)

    return imutil.to_segment(result_frames, durations, afmt=args.format)

  await matcher.finish(await misc.to_thread(make))
