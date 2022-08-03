import os
from argparse import Namespace
from io import BytesIO

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageOps

from util import command, text, util

from ..util import get_image_and_user

plugin_dir = os.path.dirname(os.path.abspath(__file__))
GENDERS = {
  "male": "他",
  "female": "她",
  "unknown": "它",
  "animal": "牠",
  "god": "祂",
}

parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"))
parser.add_argument("-gender", "-性别", help=(
  "自定义性别，对于图片链接默认为未知，对于QQ用户默认为资料性别，可以是\"male\"（他）、"
  "\"female\"（她）、\"unknown\"（它）、\"animal\"（牠）、\"god\"（祂）"))
matcher = (
  command.CommandBuilder("petpet_v2.safe_sense", "安全感")
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
    avatar, user = await get_image_and_user(bot, event, args.target, event.self_id, crop=False)
  except util.AggregateError as e:
    await matcher.finish("\n".join(e))
  gender = args.gender
  if gender is None:
    if user is not None:
      info = await bot.get_stranger_info(user_id=user)
      gender = info["sex"]
    else:
      gender = "unknown"

  avatar = ImageOps.fit(avatar, (215, 343), util.scale_resample)
  im = Image.open(os.path.join(plugin_dir, "template.png"))
  im.paste(avatar, (215, 135), avatar)

  content = f"你给我的安全感\n远不及{GENDERS[gender]}的万分之一"
  text.paste(im, (im.width // 2, 0), content, "sans", 45, align="m", anchor="mt")

  f = BytesIO()
  im.save(f, "PNG")
  await matcher.finish(MessageSegment.image(f))
