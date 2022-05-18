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

parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
matcher = (command.CommandBuilder("petpet_v2.support", "精神支柱")
  .category("petpet_v2")
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
  avatar = avatar.resize((815, 815), Image.ANTIALIAS).rotate(23, Image.BICUBIC, True)
  template = Image.open(os.path.join(plugin_dir, "template.png"))
  im = Image.new("RGB", template.size, (255, 255, 255))
  im.paste(avatar, (-172, -17), avatar)
  im.paste(template, mask=template)
  f = BytesIO()
  im.save(f, "PNG")
  await matcher.finish(MessageSegment.image(f))
