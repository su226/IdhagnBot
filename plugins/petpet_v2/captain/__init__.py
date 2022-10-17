import asyncio
from argparse import Namespace
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, util

from ..util import get_image_and_user

DIR = Path(__file__).resolve().parent

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="*", default=[""], metavar="目标",
  help="可使用@、QQ号、昵称、群名片或图片链接，可以指定最多5个"
)

matcher = command.CommandBuilder("petpet_v2.captain", "舰长") \
  .category("petpet_v2") \
  .shell(parser) \
  .auto_reject() \
  .build()
@matcher.handle()
async def handler(
  bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()
) -> None:
  async def get_avatar(pattern: str) -> Image.Image:
    avatar, _ = await get_image_and_user(bot, event, pattern, event.self_id)
    return avatar
  if len(args.target) > 5:
    await matcher.finish("最多只能有 5 张图片")
  if not args.target:
    args.target.append("")
  coros = [get_avatar(pattern) for pattern in args.target]
  target = await asyncio.gather(*coros)

  def make() -> MessageSegment:
    bg0: Image.Image | None = None
    im = Image.new("RGB", (640, len(target) * 420))
    for i, avatar in enumerate(target):
      if i == len(target) - 1:
        bg = Image.open(DIR / "2.png")
      elif i == len(target) - 2:
        bg = Image.open(DIR / "1.png")
      else:
        bg = bg0 = bg0 or Image.open(DIR / "0.png")
      avatar = avatar.resize((250, 250), util.scale_resample)
      im.paste(bg, (0, i * bg.height))
      im.paste(avatar, (350, i * bg.height + 85))
    return util.pil_image(im)

  await matcher.finish(await asyncio.to_thread(make))
