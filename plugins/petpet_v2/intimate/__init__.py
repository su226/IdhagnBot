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

OTHER_BOXES = [
  (39, 91, 75, 75), (49, 101, 75, 75), (67, 98, 75, 75), (55, 86, 75, 75), (61, 109, 75, 75),
  (65, 101, 75, 75)]
SELF_BOXES = [
  (102, 95, 70, 80, 0), (108, 60, 50, 100, 0), (97, 18, 65, 95, 0), (65, 5, 75, 75, -20),
  (95, 57, 100, 55, -70), (109, 107, 65, 75, 0)]

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
parser.add_argument("-source", default="", metavar="源", help="同上")
group = parser.add_mutually_exclusive_group()
group.add_argument(
  "-webp", action="store_const", dest="format", const="webp", default="gif",
  help="使用WebP而非GIF格式")
group.add_argument(
  "-apng", "-png", action="store_const", dest="format", const="png", help="使用APNG而非GIF格式")
matcher = (
  command.CommandBuilder("petpet_v2.intimate", "贴贴")
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
    avatar2, _ = await get_image_and_user(bot, event, args.source, event.user_id)
  except util.AggregateError as e:
    await matcher.finish("\n".join(e))
  util.circle(avatar)
  util.circle(avatar2)
  frames: list[Image.Image] = []
  for i in range(6):
    frame = Image.open(os.path.join(plugin_dir, f"{i}.png"))
    x, y, w, h = OTHER_BOXES[i]
    other_head = avatar.resize((w, h), util.scale_resample)
    frame.paste(other_head, (x, y), mask=other_head)
    x, y, w, h, angle = SELF_BOXES[i]
    self_head = avatar2.resize((w, h), util.scale_resample).rotate(angle, util.resample, True)
    frame.paste(self_head, (x, y), mask=self_head)
    frames.append(frame)
  await matcher.finish(segment_animated_image(args.format, frames, 50))
