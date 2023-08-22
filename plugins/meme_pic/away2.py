import asyncio
from argparse import Namespace
from typing import Generator, List, Optional, Tuple

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, imutil, misc, textutil
from util.user_aliases import AvatarGetter, DefaultType


def transposes(l: List[Image.Image]) -> Generator[Image.Image, None, None]:
  for i in range(8):
    for j in l:
      if i == 0:
        yield j
      elif i == 1:
        yield j.transpose(Image.Transpose.ROTATE_90)
      elif i == 2:
        yield j.transpose(Image.Transpose.ROTATE_180)
      elif i == 3:
        yield j.transpose(Image.Transpose.ROTATE_270)
      elif i == 4:
        yield j.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
      elif i == 5:
        yield j.transpose(Image.Transpose.TRANSPOSE)
      elif i == 6:
        yield j.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
      elif i == 7:
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

  target_tasks: List[asyncio.Task[Tuple[Image.Image, Optional[int]]]] = []
  async with AvatarGetter(bot, event) as g:
    for i, pattern in enumerate(args.targets, 1):
      target_tasks.append(g(pattern, DefaultType.TARGET, f"目标{i}"))

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

  await matcher.finish(await misc.to_thread(make))
