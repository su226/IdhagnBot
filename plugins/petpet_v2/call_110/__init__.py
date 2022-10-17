import asyncio
from argparse import Namespace

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, text, util

from ..util import get_image_and_user

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标",
  help="可使用@、QQ号、昵称、群名片或图片链接"
)
parser.add_argument(
  "--source", "-s", default="", metavar="源",
  help="同上"
)

matcher = command.CommandBuilder("petpet_v2.call_110", "遇到困难请拨打") \
  .category("petpet_v2") \
  .shell(parser) \
  .auto_reject() \
  .build()
@matcher.handle()
async def handler(
  bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()
) -> None:
  try:
    target, _ = await get_image_and_user(bot, event, args.target, event.self_id)
    source, _ = await get_image_and_user(bot, event, args.source, event.user_id)
  except util.AggregateError as e:
    await matcher.finish("\n".join(e))

  def make() -> MessageSegment:
    nonlocal target, source
    target = target.resize((250, 250), util.scale_resample)
    source = source.resize((250, 250), util.scale_resample)

    im = Image.new("RGB", (900, 500), (255, 255, 255))
    text.paste(im, (450, 100), "遇到困难请拨打", "sans", 100, anchor="mm")
    im.paste(target, (50, 200), target)
    im.paste(target, (325, 200), target)
    im.paste(source, (600, 200), source)

    return util.pil_image(im)

  await matcher.finish(await asyncio.to_thread(make))
