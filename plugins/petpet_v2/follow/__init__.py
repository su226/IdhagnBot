from argparse import Namespace
from io import BytesIO

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, context, text, util

from ..util import get_image_and_user

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
parser.add_argument(
  "-name", "-名字", help="自定义名字，对于图片链接默认为\"男同\"，对于QQ用户默认使用昵称")
matcher = (
  command.CommandBuilder("petpet_v2.follow", "关注")
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
  if args.name is not None:
    name = args.name
  elif user is not None:
    name = await context.get_card_or_name(bot, event, user)
  else:
    name = "男同"
  avatar = avatar.resize((200, 200), util.scale_resample)
  util.circle(avatar)
  text_im = text.render(name, "sans", 60)
  text2_im = text.render("关注了你", "sans", 60, color=(127, 127, 127))
  text_width = max(text_im.width, text2_im.width)
  text_height = max(text_im.height + 10 + text2_im.height, avatar.height)
  im = Image.new("RGB", (150 + avatar.width + text_width, 100 + text_height), (255, 255, 255))
  im.paste(avatar, (50, 50), avatar)
  im.paste(text_im, (avatar.width + 100, 50), text_im)
  im.paste(text2_im, (avatar.width + 100, 60 + text_im.height), text2_im)
  f = BytesIO()
  im.save(f, "PNG")
  await matcher.finish(MessageSegment.image(f))
