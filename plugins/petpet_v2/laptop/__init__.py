from argparse import Namespace
from io import BytesIO
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageOps

from util import command, text, util

from ..util import get_image_and_user, segment_animated_image

plugin_dir = Path(__file__).resolve().parent
# pylama: skip=1
# RemapTransform((220, 160), ((0, 39), (225, 0), (236, 145), (25, 197)))
OLD_SIZE = 220, 160
NEW_SIZE = 236, 197
TRANSFORM = (
  0.8469606952031231, -0.13401276822833844, 5.226497960904075, 0.15932974592085844,
  0.9192100726203283, -35.84919283219329, -0.0004890372852200551, -0.00027999415409538726)

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标",
  help="可使用@、QQ号、昵称、群名片或图片链接（可传入动图）")
parser.add_argument(
  "--text", "-t", metavar="内容", default="来玩休闲游戏啊",
  help="自定义内容，默认为\"来玩休闲游戏啊\"")
group = parser.add_mutually_exclusive_group()
group.add_argument(
  "--webp", "-w", action="store_const", dest="format", const="webp", default="gif",
  help="使用WebP而非GIF格式（如果传入动图）")
group.add_argument(
  "--png", "--apng", "-p", action="store_const", dest="format", const="png",
  help="使用APNG而非GIF格式（如果传入动图）")
matcher = (
  command.CommandBuilder("petpet_v2.laptop", "笔记本", "玩游戏")
  .category("petpet_v2")
  .brief("[动]")
  .shell(parser)
  .build())


@matcher.handle()
async def handler(
  bot: Bot, event: MessageEvent, args: Namespace | ParserExit = ShellCommandArgs()
) -> None:
  if isinstance(args, ParserExit):
    await matcher.finish(args.message)
  try:
    avatar, _ = await get_image_and_user(bot, event, args.target, event.self_id, raw=True)
  except util.AggregateError as e:
    await matcher.finish("\n".join(e))

  template = Image.open(plugin_dir / "template.png")
  text_im = text.render(
    args.text, "sans", 40, color=(255, 255, 255), stroke=2, stroke_color=(0, 0, 0))
  if text_im.width > (w := template.width - 20):
    text_im = util.resize_width(text_im, w)
  template.paste(text_im, (
    (template.width - text_im.width) // 2, template.height - text_im.height - 20
  ), text_im)
  frames: list[Image.Image] = []
  frametime = avatar.info.get("duration", 0)
  for raw in util.frames(avatar):
    im = Image.new("RGB", template.size, (0, 0, 0))
    frame = ImageOps.pad(raw.convert("RGBA"), OLD_SIZE, util.scale_resample)
    frame = frame.transform(NEW_SIZE, Image.Transform.PERSPECTIVE, TRANSFORM, util.resample)
    im.paste(frame, (162, 119), frame)
    im.paste(template, mask=template)
    frames.append(im)

  if len(frames) > 1:
    segment = segment_animated_image(args.format, frames, frametime)
  else:
    f = BytesIO()
    frames[0].save(f, "png")
    segment = MessageSegment.image(f)
  await matcher.finish(segment)
