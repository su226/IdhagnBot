from argparse import Namespace
from io import BytesIO
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, text, util

from ..util import get_image_and_user

plugin_dir = Path(__file__).resolve().parent

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "line1", metavar="第一行",
  help="第一行文本")
parser.add_argument(
  "line2", metavar="第一行",
  help="第二行文本，英文或日文请自行翻译")
parser.add_argument(
  "target", nargs="?", default="", metavar="目标",
  help="可使用@、QQ号、昵称、群名片或图片链接")
matcher = (
  command.CommandBuilder("petpet_v2.dianzhongdian", "典中典")
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
  except util.AggregateError as e:
    await matcher.finish("\n".join(e))

  avatar = avatar.convert("LA")
  avatar = util.resize_width(avatar, 500)
  line1_im = text.render(args.line1, "sans", 50, color=(255, 255, 255))
  line1_im = util.center(line1_im, 500, 60)
  line2_im = text.render(args.line2, "sans", 25, color=(255, 255, 255))
  line2_im = util.center(line2_im, 500, 35)

  im = Image.new("RGB", (500, avatar.height + 100))
  im.paste(avatar, mask=avatar.getchannel("A"))
  im.paste(line1_im, (0, avatar.height), line1_im)
  im.paste(line2_im, (0, avatar.height + 60), line2_im)

  f = BytesIO()
  im.save(f, "PNG")
  await matcher.finish(MessageSegment.image(f))
