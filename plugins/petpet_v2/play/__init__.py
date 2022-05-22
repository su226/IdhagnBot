import os
from argparse import Namespace

from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, helper

from ..util import get_image_and_user, segment_animated_image

plugin_dir = os.path.dirname(os.path.abspath(__file__))

BOXES = [
  (180, 60, 100, 100), (184, 75, 100, 100), (183, 98, 100, 100), (179, 118, 110, 100),
  (156, 194, 150, 48), (178, 136, 122, 69), (175, 66, 122, 85), (170, 42, 130, 96),
  (175, 34, 118, 95), (179, 35, 110, 93), (180, 54, 102, 93), (183, 58, 97, 92),
  (174, 35, 120, 94), (179, 35, 109, 93), (181, 54, 101, 92), (182, 59, 98, 92),
  (183, 71, 90, 96), (180, 131, 92, 101)]

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
  command.CommandBuilder("petpet_v2.play", "玩", "顶", "play")
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
  for i in range(23):
    frames.append(Image.open(os.path.join(plugin_dir, f"{i}.png")))
  for i, (x, y, w, h) in enumerate(BOXES):
    frame = Image.new('RGBA', (480, 400), (255, 255, 255, 0))
    frame.paste(avatar.resize((w, h), Image.ANTIALIAS), (x, y))
    frame.paste(frames[i], mask=frames[i])
    frames[i] = frame
  result_frames: list[Image.Image] = []
  for i in range(2):
    result_frames.extend(frames[0:12])
  result_frames.extend(frames[0:8])
  result_frames.extend(frames[12:18])
  result_frames.extend(frames[18:23])
  await matcher.finish(segment_animated_image(args.format, result_frames, 60))
