from argparse import Namespace
from io import BytesIO
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageOps

from util import command, context, text, util

from ..util import get_image_and_user

plugin_dir = Path(__file__).resolve().parent

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标",
  help="可使用@、QQ号、昵称、群名片或图片链接")
parser.add_argument(
  "--text", "-t", metavar="文本",
  help="自定义文本，默认为\"xxx陪睡劵（永久有效）\"")
matcher = (
  command.CommandBuilder("petpet_v2.coupon", "兑换劵")
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
    avatar, user = await get_image_and_user(bot, event, args.target, event.self_id)
  except util.AggregateError as e:
    await matcher.finish("\n".join(e))

  if args.text:
    content = args.text
  elif user:
    name = await context.get_card_or_name(bot, event, user)
    content = f"{name}陪睡劵\n（永久有效）"
  else:
    await matcher.finish("请用 --text 指定文本")

  im = Image.open(plugin_dir / "template.png")
  avatar = avatar.resize((60, 60), util.scale_resample).rotate(22, util.resample)
  util.circle(avatar)
  text_im = text.render(content, "sans", 30, align="m")
  text_im = util.center(text_im, 220, 100)
  text_im = text_im.rotate(22, util.resample, True)

  im.paste(avatar, (63, 198), avatar)
  im.paste(text_im, (118, 77), text_im)

  f = BytesIO()
  im.save(f, "PNG")
  await matcher.finish(MessageSegment.image(f))
