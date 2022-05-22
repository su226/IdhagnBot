import os
import random
from argparse import Namespace

from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, helper

from ..util import circle, get_image_and_user, segment_animated_image

plugin_dir = os.path.dirname(os.path.abspath(__file__))

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
parser.add_argument(
  "-duration", "-时长", type=int, default=50, metavar="毫秒数", help="[1, 200]之间的整数，默认为50")
parser.add_argument(
  "-original", "-原图", action="store_true", help="使用原图，可能出现文件过大发送失败")
group = parser.add_mutually_exclusive_group()
group.add_argument(
  "-ccw", "-顺时针", dest="acw", action="store_false", default=None, help="始终使用顺时针而非随机")
group.add_argument(
  "-acw", "-逆时针", dest="acw", action="store_true", help="始终使用逆时针而非随机")
group = parser.add_mutually_exclusive_group()
group.add_argument(
  "-webp", action="store_const", dest="format", const="webp", default="gif",
  help="使用WebP而非GIF格式")
group.add_argument(
  "-apng", "-png", action="store_const", dest="format", const="png", help="使用APNG而非GIF格式")
matcher = (
  command.CommandBuilder("petpet_v2.spin", "转")
  .category("petpet_v2")
  .shell(parser)
  .build())


@matcher.handle()
async def handler(
  bot: Bot, event: MessageEvent, args: Namespace | ParserExit = ShellCommandArgs()
) -> None:
  if isinstance(args, ParserExit):
    await matcher.finish(args.message)
  try:
    avatar, _ = await get_image_and_user(bot, event, args.target, event.self_id)
  except helper.AggregateError as e:
    await matcher.finish("\n".join(e))
  if args.duration < 1 or args.duration > 200:
    await matcher.finish("时长必须是[1, 200]之间的整数")
  acw = bool(random.randrange(2)) if args.acw is None else args.acw
  frames: list[Image.Image] = []
  if not args.original:
    avatar = avatar.resize((250, 250), Image.ANTIALIAS)
  for i in range(0, 360, 10):
    frame = avatar.rotate(i if acw else -i, Image.BICUBIC)
    circle(frame, args.format != "gif")
    frames.append(frame)
  await matcher.finish(segment_animated_image(args.format, frames, args.duration))
