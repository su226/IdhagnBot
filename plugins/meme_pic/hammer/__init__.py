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
  (62, 143, 158, 113), (52, 177, 173, 105), (42, 192, 192, 92), (46, 182, 184, 100),
  (54, 169, 174, 110), (69, 128, 144, 135), (65, 130, 152, 124)
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
  command.CommandBuilder("meme_pic.hammer", "锤")
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
    for i in range(7):
      template = Image.open(DIR / f"{i}.png").convert("RGBA")
      im = Image.new("RGB", template.size, (255, 255, 255))
      x, y, w, h = BOXES[i]
      target1 = target.resize((w, h), imutil.scale_resample())
      im.paste(target1, (x, y), target1)
      im.paste(template, mask=template)
      frames.append(im)
    return imutil.to_segment(frames, 70, afmt=args.format)

  await matcher.finish(await misc.to_thread(make))
