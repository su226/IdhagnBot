from typing import Any
from argparse import Namespace
from io import BytesIO
import os

from PIL import Image
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.exception import ParserExit
from nonebot.rule import ArgumentParser
from nonebot.params import ShellCommandArgs

from util import command, helper
from ..util import RemapTransform, get_image_and_user

plugin_dir = os.path.dirname(os.path.abspath(__file__))
TRANSFORM: Any = RemapTransform((330, 330), ((0, 19), (236, 0), (287, 264), (66, 351)))

parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
matcher = (command.CommandBuilder("petpet_v2.prpr", "舔", "prpr")
  .category("petpet_v2")
  .brief("少舔屏，小心屏幕进水")
  .shell(parser)
  .build())
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace | ParserExit = ShellCommandArgs()):
  if isinstance(args, ParserExit):
    await matcher.finish(args.message)
  try:
    avatar, _ = await get_image_and_user(bot, event, args.target, event.self_id)
  except helper.AggregateError as e:
    await matcher.finish("\n".join(e))
  template = Image.open(os.path.join(plugin_dir, "template.png"))
  avatar = avatar.resize(TRANSFORM.old_size, Image.ANTIALIAS).transform(TRANSFORM.new_size, TRANSFORM, resample=Image.BICUBIC)
  im = Image.new("RGB", template.size, (255, 255, 255))
  im.paste(avatar, (56, 284), avatar)
  im.paste(template, mask=template)
  f = BytesIO()
  im.save(f, "png")
  await matcher.finish(MessageSegment.image(f))