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

from ..util import get_image_and_user

plugin_dir = os.path.dirname(os.path.abspath(__file__))

parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
parser.add_argument("-source", default="", metavar="源", help="同上")
matcher = (
  command.CommandBuilder("petpet_v2.cxk", "cxk", "蔡徐坤", "篮球", "jntm", "鸡你太美")
  .category("petpet_v2")
  .brief("制作蔡徐坤打篮球图")
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
    avatar2, _ = await get_image_and_user(bot, event, args.source, event.user_id)
  except helper.AggregateError as e:
    await matcher.finish("\n".join(e))
  avatar = avatar.resize((130, 130), Image.ANTIALIAS).rotate(random.uniform(0, 360), Image.BICUBIC)
  avatar2 = avatar2.resize((130, 130), Image.ANTIALIAS)
  im = Image.new("RGB", (830, 830), (255, 255, 255))
  im.paste(avatar2, (382, 59), avatar2)
  im.paste(avatar, (609, 317), avatar)
  template = Image.open(os.path.join(plugin_dir, "template.png"))
  im.paste(template, mask=template)

  f = BytesIO()
  im.save(f, "PNG")
  await matcher.finish(MessageSegment.image(f))
