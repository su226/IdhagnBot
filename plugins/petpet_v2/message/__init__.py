import asyncio
import shlex
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Generator, Sequence, TypeVar, cast

from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent, MessageSegment
from nonebot.exception import ParserExit
from nonebot.params import CommandArg
from nonebot.rule import ArgumentParser
from PIL import Image, ImageDraw

from util import command, context, helper, text

from ..util import circle, get_image_and_user


@dataclass
class ParsedMessage:
  avatar: Image.Image
  name: str
  content: str


@dataclass
class RenderedMessage:
  avatar: Image.Image
  name: Image.Image
  content: Image.Image

  def __init__(self, message: ParsedMessage) -> None:
    self.avatar = message.avatar.resize((100, 100), Image.ANTIALIAS)
    circle(self.avatar)
    self.name = text.render(message.name, "sans", 25, color=(134, 136, 148))
    self.content = text.render(message.content, "sans", 40, box=600, markup=True)
    self.width = max(self.content.width, self.name.width + 15) + 270
    self.height = max(self.content.height, 47) + 143


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


plugin_dir = Path(__file__).resolve().parent

parser = ArgumentParser(prog="截图", add_help=False, epilog="多条消息可使用--分割")
parser.add_argument("user", metavar="用户", help="可使用@、QQ号、昵称或群名片")
parser.add_argument("--name", "-n", metavar="名字", help="自定义显示的名字")
parser.add_argument("content", nargs="+", metavar="内容", help=(
  "可使用类似HTML的富文本；由于技术限制，消息带空格请使用引号包裹"))

matcher = (
  command.CommandBuilder("petpet_v2.message", "截图")
  .category("petpet_v2")
  .usage(parser.format_help())
  .build())


@matcher.handle()
async def handler(
  bot: Bot, event: MessageEvent, args: Message = CommandArg()
) -> None:
  async def parse_message(argv: Sequence[str]) -> ParsedMessage:
    try:
      args = parser.parse_args(argv)
    except ParserExit as e:
      raise helper.AggregateError(str(e.message))
    avatar, user = await get_image_and_user(bot, event, args.user, event.self_id)
    if args.name is not None:
      name = args.name
    elif user is not None:
      name = await context.get_card_or_name(bot, event, user)
    else:
      raise helper.AggregateError("请使用 --name 指定名字")
    return ParsedMessage(avatar, name, " ".join(args.content))

  try:
    raw = list(split("--", shlex.split(str(args))))
  except ValueError as e:
    await matcher.finish(f"解析参数失败：{e}")
  if not raw:
    await matcher.finish("没有消息")

  tasks = [asyncio.create_task(parse_message(i)) for i in raw]
  errors: list[str] = []
  parsed: list[ParsedMessage] = []
  for i in tasks:
    try:
      parsed.append(await i)
    except helper.AggregateError as e:
      errors.extend(e)
  if errors:
    await matcher.finish("\n".join(errors))

  rendered = [RenderedMessage(i) for i in parsed]
  width = 0
  height = 20
  for i in rendered:
    width = max(width, i.width)
    height += i.height

  im = Image.new("RGB", (width, height), (234, 237, 244))
  draw = ImageDraw.Draw(im)

  corner_nw = Image.open(plugin_dir / "corner_nw.png")
  corner_sw = Image.open(plugin_dir / "corner_sw.png")
  corner_ne = Image.open(plugin_dir / "corner_ne.png")
  corner_se = Image.open(plugin_dir / "corner_se.png")
  badge = Image.open(plugin_dir / "badge.png")

  y = 0
  for i in rendered:
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

  f = BytesIO()
  im.save(f, "PNG")
  await matcher.finish(MessageSegment.image(f))
