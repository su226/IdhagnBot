from argparse import Namespace
from io import BytesIO

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.exception import ActionFailed, ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, context, text, util

from ..util import get_image_and_user

GENDERS = {
  "male": "他",
  "female": "她",
  "unknown": "它",
  "animal": "牠",
  "god": "祂",
}

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
parser.add_argument(
  "-name", "-名字", help="自定义名字，对于图片链接必须指定，对于QQ用户默认使用昵称")
parser.add_argument("-gender", "-性别", help=(
  "自定义性别，对于图片链接默认为未知，对于QQ用户默认为资料性别，可以是\"male\"（他）、"
  "\"female\"（她）、\"unknown\"（它）、\"animal\"（牠）、\"god\"（祂）"))
matcher = (
  command.CommandBuilder("petpet_v2.angel", "小天使", "angel")
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
  name = args.name
  gender = args.gender
  if (name is None or gender is None) and user is not None:
    try:
      info = await bot.get_group_member_info(
        group_id=context.get_event_context(event), user_id=user)
      name = name or info["card"] or info["nickname"]
      gender = gender or info["sex"]
    except ActionFailed:
      info = await bot.get_stranger_info(user_id=user)
      name = name or info["nickname"]
      gender = gender or info["sex"]
  if gender is None:
    gender = "unknown"
  if name is None:
    await matcher.finish("请使用 -name 指定名字")

  im = Image.new("RGB", (600, 730), (255, 255, 255))

  layout = text.layout(f"请问你们看到{name}了吗?", "sans bold", 70)
  width, height = layout.get_pixel_size()
  if width > 560 * 2.5:
    await matcher.finish("名字过长")
  im2 = text.render(layout)
  if width > 560:
    im2 = util.resize_width(im2, 560)
  im.paste(im2, (300 - im2.width // 2, 50 - im2.height // 2), im2)

  avatar = avatar.resize((500, 500), util.scale_resample)
  im.paste(avatar, (50, 110), avatar)

  text.paste(
    im, (300, 610), "非常可爱！简直就是小天使",
    "sans bold", 48, anchor="mt")
  text.paste(
    im, (300, 680), f"{GENDERS[gender]}没失踪也没怎么样  我只是觉得你们都该看一下",
    "sans bold", 26, anchor="mt")

  f = BytesIO()
  im.save(f, "PNG")
  await matcher.finish(MessageSegment.image(f))
