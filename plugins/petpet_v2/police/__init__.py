import os
from argparse import Namespace
from io import BytesIO

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.exception import ActionFailed, ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageOps

from util import command, context, helper, text

from ..util import get_image_and_user

plugin_dir = os.path.dirname(os.path.abspath(__file__))

AVATAR_TRANSFORM = Image.PERSPECTIVE, (1.0116, -0.0598, 0, -0.0453, 1.0905, 0, 0, 0.0004)
NAME_TRANSFORM = Image.AFFINE, (1, -0.125, 0, 0, 1, 0)

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
parser.add_argument(
  "-name", "-名字", help="自定义名字，对于图片链接必须指定，对于QQ用户默认使用昵称")
group = parser.add_mutually_exclusive_group()
group.add_argument(
  "-webp", action="store_const", dest="format", const="webp", default="gif",
  help="使用WebP而非GIF格式")
group.add_argument(
  "-apng", "-png", action="store_const", dest="format", const="png", help="使用APNG而非GIF格式")
matcher = (
  command.CommandBuilder("petpet_v2.police", "警察", "police")
  .category("petpet_v2")
  .brief("低调使用小心进局子")
  .shell(parser)
  .build())


@matcher.handle()
async def handler(
  bot: Bot, event: MessageEvent, args: Namespace | ParserExit = ShellCommandArgs()
) -> None:
  if isinstance(args, ParserExit):
    await matcher.finish(args.message)
  try:
    avatar, user = await get_image_and_user(bot, event, args.target, event.user_id)
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
  large = avatar.resize((460, 460), Image.ANTIALIAS).rotate(-17, Image.BICUBIC, True)
  pre_small = avatar.resize((118, 118), Image.ANTIALIAS)
  small = Image.new("RGBA", (120, 120))
  small.paste(pre_small, (1, 1), pre_small)
  small = small.transform((200, 200), *AVATAR_TRANSFORM, resample=Image.BICUBIC)
  im = Image.new("RGB", (600, 600), (255, 255, 255))
  im.paste(large, (84, 114), large)
  template = Image.open(os.path.join(plugin_dir, "template.png"))
  im.paste(template, (0, 0), template)
  im.paste(small, (82, 409), small)
  text_im = text.render(name, "sans", 16)
  if text_im.width > 120:
    text_im = text_im.resize((120, 24), Image.ANTIALIAS)
  else:
    text_im = ImageOps.pad(text_im, (120, 24), Image.ANTIALIAS)
  text_im = text_im.transform((123, 24), *NAME_TRANSFORM, Image.BICUBIC)
  im.paste(text_im, (90, 534), text_im)
  f = BytesIO()
  im.save(f, "png")
  await matcher.send(MessageSegment.image(f))
