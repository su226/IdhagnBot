import asyncio
import os
import random
from argparse import Namespace
from io import BytesIO
from typing import cast

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.exception import ActionFailed, ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageDraw, ImageOps

from util import command, context, text, util

from ..util import get_image_and_user

plugin_dir = os.path.dirname(os.path.abspath(__file__))
PREFIX = "我永远喜欢"


def name(value: str) -> tuple[int, str]:
  try:
    id, name = value.split(":", 1)
    id = int(id)
  except ValueError:
    raise ValueError("-name的格式是\"编号:名字\"")
  if id < 1 or id > 7:
    raise ValueError("编号必须在[1, 7]以内")
  return id, name


async def get_all(
  bot: Bot, event: MessageEvent, targets: list[str], default_names: list[str]
) -> tuple[list[Image.Image], list[str]]:
  async def get_one(i: int, target: str, name: str) -> tuple[Image.Image, str]:
    avatar, user = await get_image_and_user(bot, event, target, event.self_id)
    if name:
      return avatar, name
    if user is None:
      raise util.AggregateError(f"请指定第 {i} 人的名字")
    try:
      info = await bot.get_group_member_info(group_id=ctx, user_id=user)
      name = cast(str, info["card"] or info["nickname"])
    except ActionFailed:
      name = cast(str, (await bot.get_stranger_info(user_id=user))["nickname"])
    return avatar, name
  ctx = context.get_event_context(event)
  coros = [
    get_one(i, target, name) for i, (target, name) in enumerate(zip(targets, default_names), 1)]
  errors: list[util.AggregateError] = []
  avatars: list[Image.Image] = []
  names: list[str] = []
  for i in await asyncio.gather(*coros, return_exceptions=True):
    if isinstance(i, util.AggregateError):
      errors.append(i)
    else:
      avatars.append(i[0])
      names.append(i[1])
  if errors:
    raise util.AggregateError(*errors)
  return avatars, names

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "targets", nargs="*", default=[""], metavar="目标",
  help="可使用@、QQ号、昵称、群名片或图片链接，最多7个")
parser.add_argument("-name", type=name, action="append", default=[])
matcher = (
  command.CommandBuilder("petpet_v2.forever", "永远喜欢")
  .category("petpet_v2")
  .shell(parser)
  .build())


@matcher.handle()
async def handler(
  bot: Bot, event: MessageEvent, args: Namespace | ParserExit = ShellCommandArgs()
) -> None:
  if isinstance(args, ParserExit):
    await matcher.finish(args.message)
  if len(args.targets) > 7:
    await matcher.finish("你个海王，最多只能有7个目标")
  default_names: list[str] = [""] * len(args.targets)
  for i, name in args.name:
    default_names[i - 1] = name
  try:
    avatars, names = await get_all(bot, event, args.targets, default_names)
  except util.AggregateError as e:
    await matcher.finish("\n".join(e))

  im = Image.open(os.path.join(plugin_dir, "template.png"))
  avatar = ImageOps.fit(avatars[0], (350, 400), util.scale_resample)
  im.paste(avatar, (25, 35), avatar)
  for avatar in avatars[1:]:
    avatar = ImageOps.fit(avatar, (350, 400), util.scale_resample)
    im.paste(avatar, (10 + random.randint(0, 50), 20 + random.randint(0, 70)), avatar)

  layout = text.layout(PREFIX + names[0], "sans bold", 70)
  text_w, text_h = layout.get_pixel_size()
  if text_w > 800 * 2.5:
    await matcher.finish(f"名字太长：{names[0]}")
  text_im = text.render(layout)
  if text_w > 800:
    text_im = text_im.resize((800, text_h * 800 // text_w), util.scale_resample)
  text_x = (im.width - text_im.width) // 2
  text_y = 520 - text_im.height // 2
  im.paste(text_im, (text_x, text_y), text_im)

  prefix_w = text.layout("我永远喜欢", "sans-bold", 70).get_pixel_size()[0] * text_im.width // text_w
  line_x0 = text_x + prefix_w
  line_x1 = text_x + text_im.width
  name_x = text_x + (prefix_w + text_im.width) // 2
  draw = ImageDraw.Draw(im)

  for name in names[1:]:
    line_y = text_y + text_im.height * 0.6
    draw.line((line_x0, line_y, line_x1, line_y), (0, 0, 0), int(text_im.height * 0.1))

    layout = text.layout(name, "sans bold", 70)
    text_w, text_h = layout.get_pixel_size()
    if text_w > 400 * 2.5:
      await matcher.finish(f"名字太长：{name}")
    text_im = text.render(layout)
    if text_w > 400:
      text_im = text_im.resize((400, text_h * 400 // text_w), util.scale_resample)
    text_x = name_x - text_im.width // 2
    text_y -= int(text_im.height * 0.8)
    im.paste(text_im, (text_x, text_y), text_im)

    line_x0 = text_x
    line_x1 = text_x + text_im.width

  f = BytesIO()
  im.save(f, "png")
  await matcher.finish(MessageSegment.image(f))
