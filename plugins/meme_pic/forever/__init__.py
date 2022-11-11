import asyncio
import random
from argparse import Namespace
from pathlib import Path
from typing import Awaitable

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, context, imutil, misc, textutil
from util.user_aliases import AvatarGetter

DIR = Path(__file__).resolve().parent
PREFIX = "我永远喜欢"


def name(value: str) -> tuple[int, str]:
  try:
    id, name = value.split(":", 1)
    id = int(id)
  except ValueError:
    raise ValueError("--name 的格式是“编号:名字”")
  return id, name


parser = ArgumentParser(add_help=False)
parser.add_argument("targets", nargs="*", default=[""], metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接，最多7个"
))
parser.add_argument("--name", "-n", type=name, action="append", default=[], help=(
  "指定某人的名字，格式是“编号:名字”，编号从 1 开始"
))
matcher = (
  command.CommandBuilder("meme_pic.forever", "永远喜欢")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async def get_one(
    task: Awaitable[tuple[Image.Image, int | None]], i: int
  ) -> tuple[Image.Image, str]:
    avatar, user = await task
    if i in default_names:
      return avatar, default_names[i]
    if user is None:
      raise misc.AggregateError(f"你需要指定第 {i} 人的名字")
    name = await context.get_card_or_name(bot, event, user)
    return avatar, name

  if len(args.targets) > 7:
    await matcher.finish("你个海王，最多只能有7个目标")
  default_names: dict[int, str] = {i: name for i, name in args.name}
  async with AvatarGetter(bot, event) as g:
    tasks: list[asyncio.Task[tuple[Image.Image, str]]] = [
      g.submit(get_one(g.get(pattern, event.self_id, f"目标{i}"), i))
      for i, pattern in enumerate(args.targets, 1)
    ]

  def make() -> MessageSegment:
    results = [task.result() for task in tasks]
    avatars = [result[0] for result in results]
    names = [result[1] for result in results]
    im = Image.open(DIR / "template.png")
    avatar = avatars[0].resize((350, 350), imutil.scale_resample())
    im.paste(avatar, (35, 80), avatar)
    for avatar in avatars[1:]:
      avatar = avatar.resize((350, 350), imutil.scale_resample())
      im.paste(avatar, (35 + random.randint(-25, 25), 80 + random.randint(-25, 25)), avatar)

    text_im = textutil.render(PREFIX + names[0], "sans bold", 70)
    text_w = text_im.width
    text_im = imutil.contain_down(text_im, 800, 150)
    text_x = (im.width - text_im.width) // 2
    text_y = 520 - text_im.height // 2
    im.paste(text_im, (text_x, text_y), text_im)

    prefix_w: int = textutil.layout("我永远喜欢", "sans bold", 70).get_pixel_size()[0]
    prefix_w = prefix_w * text_im.width // text_w
    line_x0 = text_x + prefix_w
    line_x1 = text_x + text_im.width
    name_center = text_x + (prefix_w + text_im.width) // 2

    for name in names[1:]:
      line_y = int(text_y + text_im.height * 0.6)
      line_w = int(text_im.height * 0.05)
      im.paste((0, 0, 0), (line_x0, line_y - line_w, line_x1, line_y + line_w))

      text_im = textutil.render(name, "sans bold", 70)
      text_im = imutil.contain_down(text_im, 400, 150)
      text_x = name_center - text_im.width // 2
      text_y -= int(text_im.height * 0.8)
      im.paste(text_im, (text_x, text_y), text_im)

      line_x0 = text_x
      line_x1 = text_x + text_im.width

    return imutil.to_segment(im)

  await matcher.finish(await asyncio.to_thread(make))
