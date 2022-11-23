import random
from argparse import Namespace
from typing import List

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, imutil, misc
from util.misc import range_int
from util.user_aliases import AvatarGetter

parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
parser.add_argument("--duration", "-d", type=range_int(1, 200), default=50, metavar="毫秒", help=(
  "[1, 200]之间的整数，默认为50"
))
parser.add_argument("--original", "-o", action="store_true", help=(
  "使用原图，可能出现文件过大发送失败"
))
group = parser.add_mutually_exclusive_group()
group.add_argument("--ccw", "-c", dest="acw", action="store_false", default=None, help=(
  "始终使用顺时针而非随机"
))
group.add_argument("--acw", "-a", dest="acw", action="store_true", help=(
  "始终使用逆时针而非随机"
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
  command.CommandBuilder("meme_pic.spin", "转")
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
    acw = bool(random.randrange(2)) if args.acw is None else args.acw
    frames: List[Image.Image] = []
    if not args.original:
      target = target.resize((250, 250), imutil.scale_resample())
    for i in range(0, 360, 10):
      frame = target.rotate(i if acw else -i, imutil.resample())
      imutil.circle(frame, args.format != "gif")
      frames.append(frame)
    return imutil.to_segment(frames, args.duration, afmt=args.format)

  await matcher.finish(await misc.to_thread(make))
