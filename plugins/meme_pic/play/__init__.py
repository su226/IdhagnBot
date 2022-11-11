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
BOXES = [
  (180, 60, 100, 100), (184, 75, 100, 100), (183, 98, 100, 100), (179, 118, 110, 100),
  (156, 194, 150, 48), (178, 136, 122, 69), (175, 66, 122, 85), (170, 42, 130, 96),
  (175, 34, 118, 95), (179, 35, 110, 93), (180, 54, 102, 93), (183, 58, 97, 92),
  (174, 35, 120, 94), (179, 35, 109, 93), (181, 54, 101, 92), (182, 59, 98, 92),
  (183, 71, 90, 96), (180, 131, 92, 101)
]


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
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
  command.CommandBuilder("meme_pic.play", "玩", "顶")
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
    frames: list[Image.Image] = []
    for i in range(38):
      frames.append(Image.open(DIR / f"{i}.png").convert("RGBA"))
    for i, (x, y, w, h) in enumerate(BOXES):
      frame = Image.new("RGBA", (480, 400), (255, 255, 255, 0))
      frame.paste(target.resize((w, h), imutil.scale_resample()), (x, y))
      frame.paste(frames[i], mask=frames[i])
      frames[i] = frame
    result_frames: list[Image.Image] = []
    for i in range(2):
      result_frames.extend(frames[0:12])
    result_frames.extend(frames[0:8])
    result_frames.extend(frames[12:18])
    result_frames.extend(frames[18:38])
    return imutil.to_segment(frames, 60, afmt=args.format)

  await matcher.finish(await asyncio.to_thread(make))
