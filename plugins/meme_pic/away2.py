import asyncio
from argparse import Namespace
from typing import Generator

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, imutil, textutil
from util.user_aliases import AvatarGetter


def transposes(l: list[Image.Image]) -> Generator[Image.Image, None, None]:
  for i in range(8):
    for j in l:
      match i:
        case 0:
          yield j
        case 1:
          yield j.transpose(Image.Transpose.ROTATE_90)
        case 2:
          yield j.transpose(Image.Transpose.ROTATE_180)
        case 3:
          yield j.transpose(Image.Transpose.ROTATE_270)
        case 4:
          yield j.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        case 5:
          yield j.transpose(Image.Transpose.TRANSPOSE)
        case 6:
          yield j.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        case 7:
          yield j.transpose(Image.Transpose.TRANSVERSE)


DEFAULT_TEXT = "如何提高社交质量：\n远离以下头像的人"
parser = ArgumentParser(add_help=False)
parser.add_argument("targets", nargs="*", default=[""], metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接，最多8个"
))
parser.add_argument("-t", "--text", default=DEFAULT_TEXT, metavar="文本", help=(
  "自定义内容，默认为“如何提高社交质量：远离以下头像的人”"
))
matcher = (
  command.CommandBuilder("meme_pic.away2", "远离")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  if len(args.targets) > 8:
    await matcher.finish("最多只能有 8 个目标")

  target_tasks: list[asyncio.Task[tuple[Image.Image, int | None]]] = []
  async with AvatarGetter(bot, event) as g:
    for i, pattern in enumerate(args.targets, 1):
      target_tasks.append(g(pattern, event.self_id, f"目标{i}"))

  def make() -> MessageSegment:
    targets = [
      task.result()[0].resize((100, 100), imutil.scale_resample()) for task in target_tasks
    ]
    im = Image.new("RGB", (400, 290), (255, 255, 255))
    textutil.paste(im, (10, 10), args.text, "sans", 24)
    for i, avatar in zip(range(8), transposes(targets)):
      x = (i % 4) * 100
      y = 90 + 100 * (i // 4)
      im.paste(avatar, (x, y), avatar)
    return imutil.to_segment(im)

  await matcher.finish(await asyncio.to_thread(make))
