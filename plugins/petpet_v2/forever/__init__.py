from argparse import Namespace
from io import BytesIO
import asyncio
import os
import random

from PIL import Image, ImageDraw, ImageOps
from nonebot.adapters.onebot.v11 import Bot, Event, MessageSegment
from nonebot.rule import ArgumentParser, ParserExit
from nonebot.params import ShellCommandArgs
import nonebot

from util import context, text
from ..util import get_image_and_user

plugin_dir = os.path.dirname(os.path.abspath(__file__))
PREFIX = "我永远喜欢"

def name(value: str):
  try:
    id, name = value.split(":", 1)
    id = int(id)
  except:
    raise ValueError("-name的格式是\"编号:名字\"")
  if id < 1 or id > 7:
    raise ValueError("编号必须在[1, 7]以内")
  return id, name

async def get_all(bot: Bot, event: Event, targets: list[str], names: list[str | None]):
  async def get_one(i: int, target: str, name: str | None):
    errors, avatar, user = await get_image_and_user(bot, event, target, event.self_id)
    if errors:
      return errors, avatar, ""
    if name is not None:
      return [], avatar, name
    if user is None:
      return [f"请指定第 {i} 人的名字"], avatar, ""
    try:
      info = await bot.get_group_member_info(group_id=ctx, user_id=user)
      name = info["card"] or info["nickname"]
    except:
      name = (await bot.get_stranger_info(user_id=user))["nickname"]
    return errors, avatar, name
  ctx = context.get_event_context(event)
  coros = []
  for i, (target, name) in enumerate(zip(targets, names), 1):
    coros.append(get_one(i, target, name))
  errors = []
  avatars = []
  names = []
  for e, a, n in await asyncio.gather(*coros):
    errors.extend(e)
    avatars.append(a)
    names.append(n)
  return errors, avatars, names

parser = ArgumentParser("/永远喜欢", add_help=False)
parser.add_argument("targets", nargs="*", default=[""], metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接，最多7个")
parser.add_argument("-name", type=name, action="append", default=[])
matcher = nonebot.on_shell_command("永远喜欢", parser=parser)
matcher.__cmd__ = "永远喜欢"
matcher.__doc__ = parser.format_help()
matcher.__cat__ = "petpet_v2"
@matcher.handle()
async def handler(bot: Bot, event: Event, args: Namespace | ParserExit = ShellCommandArgs()):
  if isinstance(args, ParserExit):
    await matcher.finish(args.message)
  if len(args.targets) > 7:
    await matcher.finish("你个海王，最多只能有7个目标")
  names: list[str | None] = [None] * len(args.targets)
  for i, name in args.name:
    names[i - 1] = name
  errors, avatars, names = await get_all(bot, event, args.targets, names)
  if errors:
    await matcher.finish("\n".join(errors))

  im = Image.open(os.path.join(plugin_dir, "template.png"))
  avatar = ImageOps.fit(avatars[0], (350, 400), Image.ANTIALIAS)
  im.paste(avatar, (25, 35), avatar)
  for avatar in avatars[1:]:
    avatar = ImageOps.fit(avatar, (350, 400), Image.ANTIALIAS)
    im.paste(avatar, (10 + random.randint(0, 50), 20 + random.randint(0, 70)), avatar)

  layout = text.layout(PREFIX + names[0], "sans bold", 70)
  text_w, text_h = layout.get_pixel_size()
  if text_w > 800 * 2.5:
    await matcher.finish(f"名字太长：{names[0]}")
  text_im = text.render(layout)
  if text_w > 800:
    text_im = text_im.resize((800, text_h * 800 // text_w), Image.ANTIALIAS)
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
      text_im = text_im.resize((400, text_h * 400 // text_w), Image.ANTIALIAS)
    text_x = name_x - text_im.width // 2
    text_y -= int(text_im.height * 0.8)
    im.paste(text_im, (text_x, text_y), text_im)

    line_x0 = text_x
    line_x1 = text_x + text_im.width

  f = BytesIO()
  im.save(f, "png")
  await matcher.finish(MessageSegment.image(f))
