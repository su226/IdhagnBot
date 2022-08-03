import os
from argparse import Namespace

from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, util

from ..util import get_image_and_user, segment_animated_image

plugin_dir = os.path.dirname(os.path.abspath(__file__))
BOXES = [
  (82, 100, 130, 119), (82, 94, 126, 125), (82, 120, 128, 99), (81, 164, 132, 55),
  (79, 163, 132, 55), (82, 140, 127, 79), (83, 152, 125, 67), (75, 157, 140, 62),
  (72, 165, 144, 54), (80, 132, 128, 87), (81, 127, 127, 92), (79, 111, 132, 108)]

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
  command.CommandBuilder("petpet_v2.suck", "吸")
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
  avatar1 = Image.new("RGB", avatar.size, (255, 255, 255))
  avatar1.paste(avatar, mask=avatar)
  frames: list[Image.Image] = []
  for i in range(12):
    template = Image.open(os.path.join(plugin_dir, f"{i}.png"))
    im = Image.new("RGBA", template.size)
    x, y, w, h = BOXES[i]
    avatar2 = avatar1.resize((w, h), util.scale_resample)
    im.paste(avatar2, (x, y))
    im.paste(template, mask=template)
    frames.append(im)
  await matcher.finish(segment_animated_image(args.format, frames, 80))
