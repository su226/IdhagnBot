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
  (0, 174), (0, 174), (0, 174), (0, 174), (0, 174), (12, 160), (19, 152), (23, 148), (26, 145),
  (32, 140), (37, 136), (42, 131), (49, 127), (70, 126), (88, 128), (-30, 210), (-19, 207),
  (-14, 200), (-10, 188), (-7, 179), (-3, 170), (-3, 175), (-1, 174), (0, 174), (0, 174), (0, 174),
  (0, 174), (0, 174), (0, 174), (0, 174), (0, 174)
]


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
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
  command.CommandBuilder("meme_pic.klee", "可莉吃")
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
    target = target.resize((83, 83), imutil.resample())
    frames: List[Image.Image] = []
    for i, (x, y) in enumerate(BOXES):
      template = Image.open(DIR / f"{i}.png").convert("RGBA")
      frame = Image.new("RGB", template.size, (255, 255, 255))
      frame.paste(target, (x, y), target)
      frame.paste(template, mask=template)
      frames.append(frame)
    return imutil.to_segment(frames, 100, afmt=args.format)

  await matcher.finish(await misc.to_thread(make))
