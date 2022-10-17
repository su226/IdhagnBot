from argparse import Namespace
from pathlib import Path
import asyncio

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageEnhance

from util import command, util

from ..util import get_image_and_user

DIR = Path(__file__).resolve().parent

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标",
  help="可使用@、QQ号、昵称、群名片或图片链接"
)

matcher = command.CommandBuilder("petpet_v2.not_responding", "未响应", "无响应") \
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
  except util.AggregateError as e:
    await matcher.finish("\n".join(e))

  def make() -> MessageSegment:
    nonlocal target
    template = Image.open(DIR / "template.png")
    target = target.resize((template.width, template.width), util.scale_resample)
    im = Image.new("RGB", (template.width, template.height + target.height), (255, 255, 255))
    im.paste(target, (0, template.height), target)
    mask = Image.new("RGBA", target.size, (255, 255, 255, 127))
    im.paste(mask, (0, template.height), mask)
    im.paste(template)
    return util.pil_image(im)

  await matcher.finish(await asyncio.to_thread(make))
