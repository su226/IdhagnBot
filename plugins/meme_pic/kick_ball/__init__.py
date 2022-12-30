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
  (57, 136), (56, 117), (55, 99), (52, 113), (50, 126), (48, 139), (47, 112), (47, 85), (47, 57),
  (48, 97), (50, 136), (51, 176), (52, 169), (55, 181), (58, 153)
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
  command.CommandBuilder("meme_pic.kick_ball", "踢球")
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
    target = target.resize((78, 78), imutil.resample())
    frames: List[Image.Image] = []
    for i, pos in enumerate(BOXES):
      template = Image.open(DIR / f"{i}.png").convert("RGBA")
      frame = Image.new("RGB", template.size, (255, 255, 255))
      target1 = target.rotate(-24 * i, imutil.resample())
      frame.paste(target1, pos, target1)
      frame.paste(template, mask=template)
      frames.append(frame)
    return imutil.to_segment(frames, 100, afmt=args.format)

  await matcher.finish(await misc.to_thread(make))
