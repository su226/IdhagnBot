import asyncio
from argparse import Namespace
from pathlib import Path
from typing import List, Optional, Tuple

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, imutil, misc
from util.user_aliases import AvatarGetter, DefaultType

DIR = Path(__file__).resolve().parent


parser = ArgumentParser(add_help=False)
parser.add_argument("targets", nargs="*", default=[""], metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接，可以指定最多5个"
))
matcher = (
  command.CommandBuilder("meme_pic.captain", "舰长")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  if len(args.targets) > 5:
    await matcher.finish("最多只能有 5 个目标")

  target_tasks: List[asyncio.Task[Tuple[Image.Image, Optional[int]]]] = []
  async with AvatarGetter(bot, event) as g:
    for i, pattern in enumerate(args.targets, 1):
      target_tasks.append(g(pattern, DefaultType.TARGET, f"目标{i}"))

  def make() -> MessageSegment:
    targets = [task.result()[0] for task in target_tasks]
    bg0: Optional[Image.Image] = None
    im = Image.new("RGB", (640, len(targets) * 420))
    for i, avatar in enumerate(targets):
      if i == len(targets) - 1:
        bg = Image.open(DIR / "2.png")
      elif i == len(targets) - 2:
        bg = Image.open(DIR / "1.png")
      else:
        bg = bg0 = bg0 or Image.open(DIR / "0.png")
      avatar = avatar.resize((250, 250), imutil.scale_resample())
      im.paste(bg, (0, i * bg.height))
      im.paste(avatar, (350, i * bg.height + 85))
    return imutil.to_segment(im)

  await matcher.finish(await misc.to_thread(make))
