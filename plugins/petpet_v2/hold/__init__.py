from argparse import Namespace
from pathlib import Path
import asyncio

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageOps

from util import command, util

from ..util import get_image_and_user

DIR = Path(__file__).resolve().parent

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标",
  help="可使用@、QQ号、昵称、群名片或图片链接"
)

matcher = command.CommandBuilder("petpet_v2.hold", "抱紧") \
  .category("petpet_v2") \
  .shell(parser) \
  .auto_reject() \
  .build()
@matcher.handle()
async def handler(
  bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()
) -> None:
  try:
    target, _ = await get_image_and_user(bot, event, args.target, event.self_id, crop=False)
  except util.AggregateError as e:
    await matcher.finish("\n".join(e))

  def make() -> MessageSegment:
    nonlocal target
    template = Image.open(DIR / "template.png")
    im = Image.new("RGB", template.size, (255, 255, 255))
    target = ImageOps.fit(target, (159, 171), util.scale_resample)
    im.paste(target, (113, 205), target)
    im.paste(template, mask=template)
    return util.pil_image(im)

  await matcher.finish(await asyncio.to_thread(make))
