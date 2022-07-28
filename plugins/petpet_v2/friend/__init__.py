from argparse import Namespace
from io import BytesIO
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.exception import ActionFailed, ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageOps

from util import command, context, helper, text

from ..util import get_image_and_user

plugin_dir = Path(__file__).resolve().parent

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
parser.add_argument(
  "-name", "-名字", help="自定义名字，对于图片链接必须指定，对于QQ用户默认使用昵称")
matcher = (
  command.CommandBuilder("petpet_v2.friend", "交朋友")
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
  except helper.AggregateError as e:
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
  overlay = Image.open(plugin_dir / "template.png")
  avatar = avatar.resize((1000, 1000), Image.ANTIALIAS)
  im = Image.new("RGB", avatar.size, (255, 255, 255))
  im.paste(avatar, mask=avatar)
  avatar1 = im.resize((250, 250), Image.ANTIALIAS).rotate(9, Image.BICUBIC, True)
  avatar2 = im.resize((55, 55), Image.ANTIALIAS).rotate(9, Image.BICUBIC)
  im.paste(avatar1, (im.width - 257, im.height - 155))
  im.paste(avatar2, (im.width - 160, im.height - 273))
  im.paste(overlay, (im.width - overlay.width, im.height - overlay.height), overlay)
  text_im = text.render(name, "sans", 20, color=(255, 255, 255), box=230, mode=text.ELLIPSIZE_END)
  text_im = ImageOps.pad(text_im, (230, text_im.height), centering=(0, 0))
  text_im = text_im.rotate(9, Image.BICUBIC, True)
  im.paste(text_im, (im.width - 281, im.height - 345), text_im)
  f = BytesIO()
  im.save(f, "png")
  await matcher.finish(MessageSegment.image(f))
