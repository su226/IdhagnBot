from argparse import Namespace
from io import BytesIO
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageOps

from util import command, helper

from ..util import get_image_and_user

plugin_dir = Path(__file__).resolve().parent

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
matcher = (
  command.CommandBuilder("petpet_v2.perfect", "完美")
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
    avatar, _ = await get_image_and_user(bot, event, args.target, event.self_id, crop=False)
  except helper.AggregateError as e:
    await matcher.finish("\n".join(e))
  im = Image.open(plugin_dir / "template.png")
  avatar = ImageOps.fit(avatar, (310, 460), Image.ANTIALIAS)
  im.paste(avatar, (313, 64), avatar)
  f = BytesIO()
  im.save(f, "PNG")
  await matcher.finish(MessageSegment.image(f))
