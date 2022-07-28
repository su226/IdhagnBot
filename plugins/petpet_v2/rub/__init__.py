from argparse import Namespace
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, helper

from ..util import get_image_and_user, segment_animated_image

plugin_dir = Path(__file__).resolve().parent
BOXES = [(25, 66), (25, 66), (23, 68), (20, 69), (22, 68), (25, 66)]

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
group = parser.add_mutually_exclusive_group()
group.add_argument(
  "-webp", action="store_const", dest="format", const="webp", default="gif",
  help="使用WebP而非GIF格式")
group.add_argument(
  "-apng", "-png", action="store_const", dest="format", const="png", help="使用APNG而非GIF格式")
matcher = (
  command.CommandBuilder("petpet_v2.rub", "搓")
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
  except helper.AggregateError as e:
    await matcher.finish("\n".join(e))
  frames: list[Image.Image] = []
  avatar = avatar.resize((78, 78), Image.ANTIALIAS)
  for i in range(5):
    template = Image.open(plugin_dir / f"{i}.png")
    frame = Image.new("RGB", template.size, (255, 255, 255))
    avatar1 = avatar.rotate(i / 5 * 360)
    frame.paste(avatar1, BOXES[i], avatar1)
    frame.paste(template, mask=template)
    frames.append(frame)
  await matcher.finish(segment_animated_image(args.format, frames, 100))
