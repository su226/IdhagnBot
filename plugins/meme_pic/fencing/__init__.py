import asyncio
from argparse import Namespace
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, imutil
from util.user_aliases import AvatarGetter

DIR = Path(__file__).resolve().parent
FRAMETIME = 50
TARGET_BOXES = [
  (57, 4), (55, 5), (58, 7), (57, 5), (53, 8), (54, 9), (64, 5), (66, 8), (70, 9), (73, 8),
  (81, 10), (77, 10), (72, 4), (79, 8), (50, 8), (60, 7), (67, 6), (60, 6), (50, 9)
]
SOURCE_BOXES = [
  (10, 6), (3, 6), (32, 7), (22, 7), (13, 4), (21, 6), (30, 6), (22, 2), (22, 3), (26, 8), (23, 8),
  (27, 10), (30, 9), (17, 6), (12, 8), (11, 7), (8, 6), (-2, 10), (4, 9)
]


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
parser.add_argument("--source", "-s", default="", metavar="源", help=(
  "同上"
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
  command.CommandBuilder("meme_pic.fencing", "击剑", "🤺")
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
    target = target.resize((27, 27), imutil.scale_resample())
    source = source.resize((27, 27), imutil.scale_resample())
    frames: list[Image.Image] = []
    for i, (target_pos, source_pos) in enumerate(zip(TARGET_BOXES, SOURCE_BOXES)):
      template = Image.open(DIR / f"{i}.png").convert("RGBA")
      im = Image.new("RGB", template.size, (255, 255, 255))
      im.paste(target, target_pos, target)
      im.paste(source, source_pos, source)
      im.paste(template, mask=template)
      frames.append(im)
    return imutil.to_segment(frames, FRAMETIME, afmt=args.format)

  await matcher.finish(await asyncio.to_thread(make))
