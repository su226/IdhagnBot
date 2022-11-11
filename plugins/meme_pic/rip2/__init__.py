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
  command.CommandBuilder("meme_pic.rip2", "怒撕")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, event.self_id)

  def make() -> MessageSegment:
    target, _ = target_task.result()
    target = target.resize((105, 105), imutil.scale_resample())
    left = target.rotate(-24, imutil.resample(), True)
    right = target.rotate(24, imutil.resample(), True)
    template = Image.open(DIR / "template.png")
    im = Image.new("RGB", template.size, (255, 255, 255))
    im.paste(left, (18, 170), left)
    im.paste(right, (163, 65), right)
    im.paste(template, mask=template)
    return imutil.to_segment(im)

  await matcher.finish(await asyncio.to_thread(make))
