import asyncio
from argparse import Namespace
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, imutil
from util.user_aliases import AvatarGetter

DIR = Path(__file__).resolve().parent


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
matcher = (
  command.CommandBuilder("meme_pic.marry", "结婚")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, event.self_id, crop=False)

  def make() -> MessageSegment:
    target, _ = target_task.result()
    left = Image.open(DIR / "0.png")
    right = Image.open(DIR / "1.png")
    target = imutil.resize_height(target, 1080)
    target.paste(left, (0, 0), left)
    target.paste(right, (target.width - right.width, 0), right)
    return imutil.to_segment(target)

  await matcher.finish(await asyncio.to_thread(make))