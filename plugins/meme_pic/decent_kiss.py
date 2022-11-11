import asyncio
from argparse import Namespace

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageOps

from util import command, imutil, textutil
from util.user_aliases import AvatarGetter

parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
matcher = (
  command.CommandBuilder("meme_pic.decent_kiss", "像样的亲亲")
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
    im = Image.new("RGB", (500, 500), (255, 255, 255))
    textutil.paste(im, (250, 0), "很抱歉打扰你…", "sans bold", 64, anchor="mt")
    target = ImageOps.fit(target, (500, 300), imutil.scale_resample())
    im.paste(target, (0, 100), target)
    textutil.paste(im, (250, 400), "可是你今天甚至没有给我", "sans bold", 32, anchor="mt")
    textutil.paste(im, (250, 445), "一个像样的亲亲诶", "sans bold", 32, anchor="mt")
    return imutil.to_segment(im)

  await matcher.finish(await asyncio.to_thread(make))
