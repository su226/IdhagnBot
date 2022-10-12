import asyncio
import math
import shlex
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Generator, Sequence, TypeVar

from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent, MessageSegment
from nonebot.exception import ParserExit
from nonebot.params import CommandArg
from nonebot.rule import ArgumentParser
from PIL import Image, ImageDraw

from util import command, context, text, util

from ..util import get_avatar, get_image_and_user, segment_animated_image


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
    self.avatar = message.avatar.resize((100, 100), util.scale_resample)
    util.circle(self.avatar)
    self.name = text.render(message.name, "sans", 25, color=(134, 136, 148))
    self.content = text.render(message.content, "sans", 40, box=600, markup=True)
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


async def render(
  bot: Bot, event: MessageEvent, args: Message,
  *, max_height: int = 10000, padding_bottom: int = 20
) -> Image.Image:
  async def parse_message(argv: Sequence[str]) -> ParsedMessage:
    try:
      args = parser.parse_args(argv)
    except ParserExit as e:
      raise util.AggregateError(str(e.message))
    avatar, user = await get_image_and_user(bot, event, args.user, event.self_id)
    if args.name is not None:
      name = args.name
    elif user is not None:
      name = await context.get_card_or_name(bot, event, user)
    else:
      raise util.AggregateError("请使用 --name 指定名字")
    return ParsedMessage(avatar, name, " ".join(args.content), args.repeat)

  try:
    raw = list(split("--", shlex.split(str(args))))
  except ValueError as e:
    raise util.AggregateError(f"解析参数失败：{e}")
  if not raw:
    raise util.AggregateError("没有消息")

  tasks = [asyncio.create_task(parse_message(i)) for i in raw]
  errors: list[str] = []
  parsed: list[ParsedMessage] = []
  for i in tasks:
    try:
      parsed.append(await i)
    except util.AggregateError as e:
      errors.extend(e)
  if errors:
    raise util.AggregateError(*errors)

  rendered = []
  width = 0
  height = padding_bottom
  for i in parsed:
    j = RenderedMessage(i)
    width = max(width, j.width)
    height += j.height * i.repeat
    if height > max_height:
      raise util.AggregateError("消息过长")
    rendered.append(j)

  im = Image.new("RGB", (width, height), (234, 237, 244))
  draw = ImageDraw.Draw(im)

  corner_nw = Image.open(plugin_dir / "corner_nw.png")
  corner_sw = Image.open(plugin_dir / "corner_sw.png")
  corner_ne = Image.open(plugin_dir / "corner_ne.png")
  corner_se = Image.open(plugin_dir / "corner_se.png")
  badge = Image.open(plugin_dir / "badge.png")

  y = 0
  for i in rendered:
    for _ in range(i.repeat):
      content_h = max(i.content.height, 47)
      im.paste(i.avatar, (20, y + 20), i.avatar)
      im.paste(badge, (160, y + 25))
      im.paste(i.name, (260, y + 40 - i.name.height // 2), i.name)
      draw.rectangle((157, y + 80, 244 + i.content.width, y + 142 + content_h), (255, 255, 255))
      im.paste(corner_nw, (130, y + 60))
      im.paste(corner_sw, (130, y + content_h + 88))
      im.paste(corner_ne, (130 + i.content.width + 70, y + 60))
      im.paste(corner_se, (130 + i.content.width + 70, y + content_h + 88))
      im.paste(i.content, (200, y + 108 + (content_h - i.content.height) // 2), i.content)

      y += i.height

  return im


plugin_dir = Path(__file__).resolve().parent

parser = ArgumentParser(prog="截图", add_help=False, epilog="多条消息可使用--分割")
parser.add_argument("user", metavar="用户", help="可使用@、QQ号、昵称或群名片")
parser.add_argument("--name", "-n", metavar="名字", help="自定义显示的名字")
parser.add_argument("--repeat", "-r", metavar="次数", type=int, default=1, help="复读次数")
parser.add_argument("content", nargs="+", metavar="内容", help=(
  "可使用类似HTML的富文本；由于技术限制，消息带空格请使用引号包裹"))

screenshot = (
  command.CommandBuilder("petpet_v2.message.screenshot", "截图")
  .category("petpet_v2")
  .usage(parser.format_help())
  .build())


@screenshot.handle()
async def handle_screenshot(
  bot: Bot, event: MessageEvent, args: Message = CommandArg()
) -> None:
  try:
    im = await render(bot, event, args)
  except util.AggregateError as e:
    await screenshot.finish("\n".join(e))

  f = BytesIO()
  im.save(f, "PNG")
  await screenshot.finish(MessageSegment.image(f))


scroll = (
  command.CommandBuilder("petpet_v2.message.scroll", "滚屏")
  .category("petpet_v2")
  .usage(parser.format_help())
  .build())


@scroll.handle()
async def handle_scroll(
  bot: Bot, event: MessageEvent, args: Message = CommandArg()
) -> None:
  try:
    im, avatar = await asyncio.gather(
      render(bot, event, args, max_height=5000, padding_bottom=0), get_avatar(event.user_id))
  except util.AggregateError as e:
    await scroll.finish("\n".join(e))

  repeat = max(2, math.ceil(2384 / im.height))
  repeated = Image.new("RGB", (im.width, im.height * repeat))
  for i in range(repeat):
    repeated.paste(im, (0, i * im.height))

  bottom = Image.open(plugin_dir / "bottom.jpg")
  avatar = avatar.resize((75, 75), util.scale_resample)
  util.circle(avatar)
  bottom.paste(avatar, (15, 40), avatar)

  frames: list[Image.Image] = []
  scroll_height = math.ceil(1192 / im.height) * im.height
  for i in range(50):
    frame = Image.new("RGB", (1079, 1192), (234, 237, 244))
    frame.paste(repeated, (0, -scroll_height * i // 50))
    frame.paste(bottom, (0, 1000))
    frames.append(frame)

  await scroll.finish(segment_animated_image("GIF", frames, 80))
