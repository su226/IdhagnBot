import os
from argparse import Namespace
from io import BytesIO

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, util

from ..util import get_image_and_user

plugin_dir = os.path.dirname(os.path.abspath(__file__))
# pylama: skip=1
# RemapTransform((330, 330), ((0, 19), (236, 0), (287, 264), (66, 351)))
OLD_SIZE = 330, 330
NEW_SIZE = 287, 351
TRANSFORM = (
  1.0952291221755943, -0.2177262712758823, 4.1367991542420945, 0.07837100517494805,
  0.9734503800677476, -18.49555722128834, -0.0008652944018017274, 0.00014852909086833315)

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
matcher = (
  command.CommandBuilder("petpet_v2.prpr", "舔", "prpr")
  .category("petpet_v2")
  .brief("少舔屏，小心屏幕进水")
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
  except util.AggregateError as e:
    await matcher.finish("\n".join(e))
  template = Image.open(os.path.join(plugin_dir, "template.png"))
  avatar = avatar.resize(OLD_SIZE, util.scale_resample).transform(
    NEW_SIZE, Image.Transform.PERSPECTIVE, TRANSFORM, resample=util.resample)
  im = Image.new("RGB", template.size, (255, 255, 255))
  im.paste(avatar, (56, 284), avatar)
  im.paste(template, mask=template)
  f = BytesIO()
  im.save(f, "png")
  await matcher.finish(MessageSegment.image(f))
