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
  (39, 40), (39, 40), (39, 40), (39, 30), (39, 30), (39, 32), (39, 32), (39, 32), (39, 32),
  (39, 32), (39, 32), (39, 32), (39, 32), (39, 32), (39, 32), (39, 30), (39, 27), (39, 32),
  (37, 49), (37, 64), (37, 67), (37, 67), (39, 69), (37, 70), (37, 70)
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
  command.CommandBuilder("meme_pic.trash", "垃圾")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, event.self_id)

  def make() -> MessageSegment:
    avatar, _ = target_task.result()
    avatar = avatar.resize((79, 79), imutil.scale_resample())
    frames: list[Image.Image] = []
    for i in range(25):
      template = Image.open(DIR / f"{i}.png")
      im = Image.new("RGB", template.size, (255, 255, 255, 0))
      im.paste(avatar, BOXES[i], avatar)
      im.paste(template, mask=template)
      frames.append(im)
    return imutil.to_segment(frames, 40, afmt=args.format)

  await matcher.finish(await asyncio.to_thread(make))
