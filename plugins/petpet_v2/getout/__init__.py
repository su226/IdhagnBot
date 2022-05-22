import os
import random
from argparse import Namespace
from io import BytesIO

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, helper

from ..util import circle, get_image_and_user

plugin_dir = os.path.dirname(os.path.abspath(__file__))

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
parser.add_argument(
  "-template", "-模板", type=int, metavar="编号",
  help="使用指定表情包而非随机，编号是[0, 91]之间的整数")
matcher = (
  command.CommandBuilder("petpet_v2.getout", "爬")
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
  template_id = random.randrange(92) if args.template is None else args.template
  if template_id < 0 or template_id > 91:
    await matcher.finish("模板编号需要是[0, 91]之间的整数")
  im = Image.open(os.path.join(plugin_dir, f"{template_id}.jpg"))
  avatar = avatar.resize((100, 100), Image.ANTIALIAS)
  circle(avatar)
  im.paste(avatar, (0, 400), avatar)
  f = BytesIO()
  im.save(f, "png")
  await matcher.finish(MessageSegment.image(f))
