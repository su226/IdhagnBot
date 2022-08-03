import os
from argparse import Namespace
from io import BytesIO

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.exception import ActionFailed, ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, context, text, util

from ..util import get_image_and_user

plugin_dir = os.path.dirname(os.path.abspath(__file__))

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
parser.add_argument(
  "-name", "-名字", help="自定义名字，对于图片链接必须指定，对于QQ用户默认使用昵称")
matcher = (
  command.CommandBuilder("petpet_v2.wantwant", "旺仔", "旺旺")
  .category("petpet_v2")
  .brief("李子明的最爱")
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
    try:
      info = await bot.get_group_member_info(
        group_id=context.get_event_context(event), user_id=user)
      name = info["card"] or info["nickname"]
    except ActionFailed:
      info = await bot.get_stranger_info(user_id=user)
      name = info["nickname"]
  else:
    await matcher.finish("请使用 -name 指定名字")
  im = Image.open(os.path.join(plugin_dir, "template.png"))
  text_im = text.render(name, "sans heavy", 80, color=(255, 255, 255))
  if text_im.width > 355:
    text_im = text_im.resize((355, text_im.height), util.scale_resample)
  im.paste(text_im, (157, 51), text_im)
  avatar = avatar.resize((226, 226), util.scale_resample)
  im.paste(avatar, (136, 182), avatar)
  f = BytesIO()
  im.save(f, "png")
  await matcher.send(MessageSegment.image(f))
