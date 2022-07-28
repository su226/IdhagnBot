from typing import cast, overload
from argparse import Namespace
from io import BytesIO

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.exception import ActionFailed, ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageDraw, PyAccess

from util import command, context, helper, text

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
parser.add_argument(
  "-gender", "-性别", help="自定义性别，对于图片链接默认为未知，对于QQ用户默认为资料性别，"
  "可以是\"male\"（他）、\"female\"（她）、\"unknown\"（它）、\"animal\"（牠）、\"god\"（祂）")
matcher = (
  command.CommandBuilder("petpet_v2.ask", "问", "问问")
  .category("petpet_v2")
  .shell(parser)
  .build())


@overload
def vertical_gradient(
  mode: str, top: int, bottom: int, width: int, height: int
) -> Image.Image: ...


@overload
def vertical_gradient(
  mode: str, top: tuple[int], bottom: tuple[int], width: int, height: int
) -> Image.Image: ...


def vertical_gradient(
  mode: str, top: int | tuple[int], bottom: int | tuple[int], width: int, height: int
) -> Image.Image:
  gradient = Image.new(mode, (1, height))
  px = cast(PyAccess.PyAccess, gradient.load())
  is_tuple = isinstance(top, tuple)
  if is_tuple:
    delta = tuple(x - y for x, y in zip(cast(tuple[int], bottom), top))
    for i in range(height):
      ratio = i / (height - 1)
      px[0, i] = tuple(int(ratio * x + y) for x, y in zip(cast(tuple[int], delta), top))
  else:
    delta = cast(int, bottom) - top
    for i in range(height):
      px[0, i] = int(delta * (i / (height - 1))) + top
  return gradient.resize((width, height))


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

  avatar = avatar.resize((640, 640), Image.ANTIALIAS)
  gradient_h = 150
  x = 30
  y = avatar.height - gradient_h
  alpha = Image.new("L", avatar.size)
  alpha.paste(vertical_gradient("L", 192, 128, avatar.width, gradient_h), (0, y))
  overlay = Image.new("RGB", avatar.size)
  overlay.putalpha(alpha)
  avatar = Image.alpha_composite(avatar, overlay)

  text_im = text.paste(avatar, (x, y + 5), name, "sans bold", 25, color=(255, 165, 0))

  draw = ImageDraw.Draw(avatar)
  draw.line((x - 5, y + 45, x + text_im.width + 5, y + 45), fill=(255, 165, 0), width=2)
  text.paste(avatar, (x, y + 50), f"{name}不知道哦", "sans bold", 25, color=(255, 255, 255))

  padding_x = 30
  padding_y = 80
  im = Image.new(
    "RGBA", (avatar.width + padding_x * 2, avatar.height + padding_y * 2), (255, 255, 255))
  text.paste(im, (padding_x, padding_y // 2), f"让{name}告诉你吧", "sans", 35, anchor="lm")
  im.paste(avatar, (padding_x, padding_y), avatar)
  text.paste(
    im, (padding_x, avatar.height + padding_y + padding_y // 2),
    f"啊这，{GENDERS[gender]}说不知道", "sans", 35, anchor="lm")

  f = BytesIO()
  im.save(f, "png")
  await matcher.send(MessageSegment.image(f))
