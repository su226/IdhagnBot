from argparse import Namespace
from io import BytesIO
import os

from PIL import Image
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.exception import ParserExit
from nonebot.rule import ArgumentParser
from nonebot.params import ShellCommandArgs

from util import command, helper
from ..util import get_image_and_user

plugin_dir = os.path.dirname(os.path.abspath(__file__))

FRAME_ORDER = [0, 1, 2, 3, 1, 2, 3, 0, 1, 2, 3, 0, 0, 1, 2, 3, 0, 0, 0, 0, 4, 5, 5, 5, 6, 7, 8, 9]
BOXES = [(11, 73, 106, 100), (8, 79, 112, 96)]

parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
matcher = (command.CommandBuilder("petpet_v2.protogen", "protogen")
  .category("petpet_v2")
  .brief("愿者上钩")
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
  avatar = avatar.resize((200, 200), Image.ANTIALIAS)
  im = Image.new("RGB", (960, 888), (255, 255, 255))
  im.paste(avatar, (215, 604), avatar)
  template = Image.open(os.path.join(plugin_dir, "template.png"))
  im.paste(template, mask=template)
  f = BytesIO()
  im.save(f, "PNG")
  await matcher.finish(MessageSegment.image(f))
