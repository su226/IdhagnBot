from argparse import Namespace
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, util

from ..util import get_image_and_user, segment_animated_image

plugin_dir = Path(__file__).resolve().parent


parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标",
  help="可使用@、QQ号、昵称、群名片或图片链接")
group = parser.add_mutually_exclusive_group()
group.add_argument(
  "--webp", "-w", action="store_const", dest="format", const="webp", default="gif",
  help="使用WebP而非GIF格式")
group.add_argument(
  "--png", "--apng", "-p", action="store_const", dest="format", const="png",
  help="使用APNG而非GIF格式")
matcher = (
  command.CommandBuilder("petpet_v2.disc", "唱片")
  .category("petpet_v2")
  .shell(parser)
  .build())


@matcher.handle()
async def handler(
  bot: Bot, event: MessageEvent, args: Namespace | ParserExit = ShellCommandArgs()
) -> None:
  if isinstance(args, ParserExit):
    await matcher.finish(args.message)
  try:
    avatar, _ = await get_image_and_user(bot, event, args.target, event.self_id)
  except util.AggregateError as e:
    await matcher.finish("\n".join(e))

  avatar = avatar.resize((215, 215), util.scale_resample)
  template = Image.open(plugin_dir / "template.png")
  frames: list[Image.Image] = []
  for i in range(0, 360, 10):
    im = Image.new("RGB", template.size, (255, 255, 255))
    rotated = avatar.rotate(-i, util.resample)
    im.paste(rotated, (100, 100), rotated)
    im.paste(template, mask=template)
    frames.append(im)

  await matcher.finish(segment_animated_image(args.format, frames, 50))
