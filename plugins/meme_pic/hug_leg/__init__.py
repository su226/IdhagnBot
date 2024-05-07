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
FRAMETIME = 60
BOXES = [
  (50, 73, 68, 92), (58, 60, 62, 95), (65, 10, 67, 118), (61, 20, 77, 97), (55, 44, 65, 106),
  (66, 85, 60, 98),
]


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
  command.CommandBuilder("meme_pic.hug_leg", "抱大腿")
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
    frames: List[Image.Image] = []
    for i, box in enumerate(BOXES):
      template = Image.open(DIR / f"{i}.png")
      im = Image.new("RGB", template.size, (255, 255, 255))
      x, y, w, h = box
      target1 = target.resize((w, h), imutil.scale_resample())
      im.paste(target1, (x, y), target1)
      im.paste(template, mask=template)
      frames.append(im)
    return imutil.to_segment(frames, FRAMETIME, afmt=args.format)

  await matcher.finish(await misc.to_thread(make))
