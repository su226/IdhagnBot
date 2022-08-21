import asyncio
from argparse import Namespace
from io import BytesIO
from typing import Generator

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, text, util

from ..util import get_image_and_user


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


DEFAULT_TEXT = "如何提高社交质量 : \n远离以下头像的人"
parser = ArgumentParser(add_help=False)
parser.add_argument(
  "targets", nargs="*", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接，最多8个")
parser.add_argument(
  "-t", "--text", default=DEFAULT_TEXT, help="自定义文本")
matcher = (
  command.CommandBuilder("petpet_v2.away2", "远离")
  .category("petpet_v2")
  .shell(parser)
  .build())


@matcher.handle()
async def handler(
  bot: Bot, event: MessageEvent, args: Namespace | ParserExit = ShellCommandArgs()
) -> None:
  if isinstance(args, ParserExit):
    await matcher.finish(args.message)
  targets: list[str] = args.targets
  if len(targets) > 8:
    await matcher.finish("最多只能有8个目标")
  if not targets:
    targets.append("")

  tasks = [
    asyncio.create_task(get_image_and_user(bot, event, target, event.self_id))
    for target in targets]
  avatars: list[Image.Image] = []
  errors: list[str] = []
  for i in tasks:
    try:
      avatars.append((await i)[0].resize((100, 100), util.scale_resample))
    except util.AggregateError as e:
      errors.extend(e)
  if errors:
    await matcher.finish("\n".join(errors))

  im = Image.new("RGB", (400, 290), (255, 255, 255))
  text.paste(im, (10, 10), args.text, "sans", 24)
  for i, avatar in zip(range(8), transposes(avatars)):
    x = (i % 4) * 100
    y = 90 + 100 * (i // 4)
    im.paste(avatar, (x, y), avatar)

  f = BytesIO()
  im.save(f, "png")
  await matcher.finish(MessageSegment.image(f))
