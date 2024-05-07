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
SOURCE_BOXES = [(6, 18), (6, 18), (6, 18), (7, 18)]
TARGET_BOXES = [(40, 37), (41, 37), (45, 45), (44, 41)]


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
parser.add_argument("--source", "-s", default="", metavar="源", help="同上")
group = parser.add_mutually_exclusive_group()
group.add_argument(
  "--webp", action="store_const", dest="format", const="webp", default="gif",
  help="使用WebP而非GIF格式",
)
group.add_argument(
  "--png", "--apng", "-p", action="store_const", dest="format", const="png",
  help="使用APNG而非GIF格式",
)
matcher = (
  command.CommandBuilder("meme_pic.slap", "打", "打脸")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, DefaultType.TARGET, "目标")
    source_task = g(args.source, DefaultType.SOURCE, "源")

  def make() -> MessageSegment:
    target, _ = target_task.result()
    source, _ = source_task.result()
    target = target.resize((22, 22), imutil.scale_resample())
    source = source.resize((30, 30), imutil.scale_resample())
    imutil.circle(target)
    imutil.circle(source)
    frames: List[Image.Image] = []
    for i in range(4):
      frame = Image.open(DIR / f"{i}.png").convert("RGB")
      frame.paste(target, TARGET_BOXES[i], target)
      frame.paste(source, SOURCE_BOXES[i], source)
      frames.append(frame)
    return imutil.to_segment(frames, 50, afmt=args.format)

  await matcher.finish(await misc.to_thread(make))
