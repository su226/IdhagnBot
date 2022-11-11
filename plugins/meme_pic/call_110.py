import asyncio
from argparse import Namespace

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, imutil, textutil
from util.user_aliases import AvatarGetter

parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
parser.add_argument("--source", "-s", default="", metavar="源", help="同上")
matcher = (
  command.CommandBuilder("meme_pic.call_110", "遇到困难请拨打")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, event.self_id, "目标")
    source_task = g(args.source, event.user_id, "源")

  def make() -> MessageSegment:
    target, _ = target_task.result()
    source, _ = source_task.result()
    target = target.resize((250, 250), imutil.scale_resample())
    source = source.resize((250, 250), imutil.scale_resample())

    im = Image.new("RGB", (900, 500), (255, 255, 255))
    textutil.paste(im, (450, 100), "遇到困难请拨打", "sans", 100, anchor="mm")
    im.paste(target, (50, 200), target)
    im.paste(target, (325, 200), target)
    im.paste(source, (600, 200), source)

    return imutil.to_segment(im)

  await matcher.finish(await asyncio.to_thread(make))
