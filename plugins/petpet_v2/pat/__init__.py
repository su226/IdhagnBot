from argparse import Namespace
import os

from PIL import Image
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.exception import ParserExit
from nonebot.rule import ArgumentParser
from nonebot.params import ShellCommandArgs

from util import command, helper
from ..util import segment_animated_image, get_image_and_user

plugin_dir = os.path.dirname(os.path.abspath(__file__))

FRAME_ORDER = [
  0, 1, 2, 3, 1, 2, 3, 0, 1, 2, 3, 0, 0, 1, 2, 3, 0, 0, 0, 0, 4, 5, 5, 5, 6, 7,
  8, 9
]
BOXES = [(11, 73, 106, 100), (8, 79, 112, 96)]

parser = ArgumentParser(add_help=False, epilog="~~你TM拍我瓜是吧~~")
parser.add_argument("target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
group = parser.add_mutually_exclusive_group()
group.add_argument("-webp", action="store_const", dest="format", const="webp", default="gif", help="使用WebP而非GIF格式")
group.add_argument("-apng", "-png", action="store_const", dest="format", const="png", help="使用APNG而非GIF格式")
matcher = (command.CommandBuilder("petpet_v2.pat", "拍拍", "拍", "pat")
  .category("petpet_v2")
  .shell(parser)
  .build())
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace | ParserExit = ShellCommandArgs()) -> None:
  if isinstance(args, ParserExit):
    await matcher.finish(args.message)
  try:
    avatar, _ = await get_image_and_user(bot, event, args.target, event.self_id)
  except helper.AggregateError as e:
    await matcher.finish("\n".join(e))
  frames: list[Image.Image] = []
  for i in range(10):
    frame = Image.new('RGBA', (235, 196), (255, 255, 255, 0))
    x, y, w, h = BOXES[1 if i == 2 else 0]
    frame.paste(avatar.resize((w, h), Image.ANTIALIAS), (x, y))
    raw_frame = Image.open(os.path.join(plugin_dir, f"{i}.png"))
    frame.paste(raw_frame, mask=raw_frame)
    frames.append(frame)
  frames = [frames[n] for n in FRAME_ORDER]
  await matcher.finish(segment_animated_image(args.format, frames, 85))
