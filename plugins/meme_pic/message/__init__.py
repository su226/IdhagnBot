import asyncio
import math
import shlex
from argparse import Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Sequence, TypeVar

from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent, MessageSegment
from nonebot.exception import ParserExit
from nonebot.params import CommandArg
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, context, imutil, misc, textutil
from util.misc import range_int
from util.user_aliases import AvatarGetter, get_avatar


@dataclass
class ParsedMessage:
  avatar: Image.Image
  name: str
  content: str
  repeat: int


@dataclass
class RenderedMessage:
  avatar: Image.Image
  name: Image.Image
  content: Image.Image
  repeat: int

  def __init__(self, message: ParsedMessage) -> None:
    self.avatar = message.avatar.resize((100, 100), imutil.scale_resample())
    imutil.circle(self.avatar)
    self.name = textutil.render(message.name, "sans", 25, color=(134, 136, 148))
    self.content = textutil.render(message.content, "sans", 40, box=600, markup=True)
    self.width = max(self.content.width, self.name.width + 15) + 270
    self.height = max(self.content.height, 47) + 143
    self.repeat = message.repeat


T = TypeVar("T")


def split(delim: T, l: Sequence[T]) -> Generator[Sequence[T], None, None]:
  prev_index = 0
  while True:
    try:
      index = l.index(delim, prev_index)
    except ValueError:
      yield l[prev_index:]
      return
    yield l[prev_index:index]
    prev_index = index + 1


def parse_args(msg: Message) -> list[Namespace]:
  try:
    all_argv = list(split("--", shlex.split(str(msg))))
  except ValueError as e:
    raise misc.AggregateError(f"解析参数失败：{e}")

  errors: list[str] = []
  all_args: list[Namespace] = []
  for argv in all_argv:
    try:
      all_args.append(parser.parse_args(argv))
    except ParserExit as e:
      errors.append(e.message or "")
  if errors:
    raise misc.AggregateError(errors)

  return all_args


def parse_message(
  g: AvatarGetter, bot: Bot, event: MessageEvent, all_args: list[Namespace]
) -> list[asyncio.Task[ParsedMessage]]:
  async def parse_one(
    task: asyncio.Task[tuple[Image.Image, int | None]], args: Namespace
  ) -> ParsedMessage:
    avatar, user = await task
    if args.name is not None:
      name = args.name
    elif user is not None:
      name = await context.get_card_or_name(bot, event, user)
    else:
      raise misc.AggregateError("请使用 --name 指定名字")
    return ParsedMessage(avatar, name, " ".join(args.content), args.repeat)

  return [
    g.submit(parse_one(g(args.user, event.self_id, f"头像{i}"), args))
    for i, args in enumerate(all_args, 1)
  ]


def render(
  messages: list[ParsedMessage], max_height: int = 10000, padding_bottom: int = 20
) -> Image.Image:
  rendered: list[RenderedMessage] = []
  width = 0
  height = padding_bottom
  for i in messages:
    j = RenderedMessage(i)
    width = max(width, j.width)
    height += j.height * i.repeat
    if height > max_height:
      raise misc.AggregateError("消息过长")
    rendered.append(j)

  im = Image.new("RGB", (width, height), (234, 237, 244))

  corner_nw = Image.open(DIR / "corner_nw.png")
  corner_sw = Image.open(DIR / "corner_sw.png")
  corner_ne = Image.open(DIR / "corner_ne.png")
  corner_se = Image.open(DIR / "corner_se.png")
  badge = Image.open(DIR / "badge.png")

  y = 0
  for i in rendered:
    for _ in range(i.repeat):
      content_h = max(i.content.height, 47)
      im.paste(i.avatar, (20, y + 20), i.avatar)
      im.paste(badge, (160, y + 25))
      im.paste(i.name, (260, y + 40 - i.name.height // 2), i.name)
      im.paste((255, 255, 255), (157, y + 80, 245 + i.content.width, y + 143 + content_h))
      im.paste(corner_nw, (130, y + 60))
      im.paste(corner_sw, (130, y + content_h + 88))
      im.paste(corner_ne, (130 + i.content.width + 70, y + 60))
      im.paste(corner_se, (130 + i.content.width + 70, y + content_h + 88))
      im.paste(i.content, (200, y + 108 + (content_h - i.content.height) // 2), i.content)

      y += i.height

  return im


DIR = Path(__file__).resolve().parent


parser = ArgumentParser(prog="/截图", add_help=False, epilog="多条消息可使用 -- 分割")
parser.add_argument("user", metavar="用户", help="可使用@、QQ号、昵称或群名片")
parser.add_argument("--name", "-n", metavar="名字", help="自定义显示的名字")
parser.add_argument("--repeat", "-r", metavar="次数", type=range_int(1, 10), default=1, help=(
  "复读次数"
))
parser.add_argument("content", nargs="+", metavar="内容", help=(
  "可使用类似HTML的富文本；由于技术限制，消息带空格请使用引号包裹"
))
screenshot = (
  command.CommandBuilder("meme_pic.message.screenshot", "截图")
  .category("meme_pic")
  .usage(parser.format_help())
  .build()
)
@screenshot.handle()
async def handle_screenshot(bot: Bot, event: MessageEvent, msg: Message = CommandArg()) -> None:
  try:
    all_args = parse_args(msg)
  except misc.AggregateError as e:
    await screenshot.finish("\n".join(e))
  async with AvatarGetter(bot, event) as g:
    message_tasks = parse_message(g, bot, event, all_args)

  def make() -> MessageSegment:
    messages = [task.result() for task in message_tasks]
    return imutil.to_segment(render(messages))

  await screenshot.finish(await asyncio.to_thread(make))


scroll = (
  command.CommandBuilder("meme_pic.message.scroll", "滚屏")
  .category("meme_pic")
  .usage(parser.format_help())
  .build()
)
@scroll.handle()
async def handle_scroll(bot: Bot, event: MessageEvent, msg: Message = CommandArg()) -> None:
  try:
    all_args = parse_args(msg)
  except misc.AggregateError as e:
    await screenshot.finish("\n".join(e))
  async with AvatarGetter(bot, event) as g:
    message_tasks = parse_message(g, bot, event, all_args)
    avatar_task = g.submit(get_avatar(event.user_id))

  def make() -> MessageSegment:
    messages = [task.result() for task in message_tasks]
    im = render(messages, 5000, 0)
    avatar = avatar_task.result()
    repeat = max(2, math.ceil(2384 / im.height))
    repeated = Image.new("RGB", (im.width, im.height * repeat))
    for i in range(repeat):
      repeated.paste(im, (0, i * im.height))

    bottom = Image.open(DIR / "bottom.jpg")
    avatar = avatar.resize((75, 75), imutil.scale_resample())
    imutil.circle(avatar)
    bottom.paste(avatar, (15, 40), avatar)

    frames: list[Image.Image] = []
    scroll_height = math.ceil(1192 / im.height) * im.height
    for i in range(50):
      frame = Image.new("RGB", (1079, 1192), (234, 237, 244))
      frame.paste(repeated, (0, -scroll_height * i // 50))
      frame.paste(bottom, (0, 1000))
      frames.append(frame)

    return imutil.to_segment(frames, 80)

  await scroll.finish(await asyncio.to_thread(make))
