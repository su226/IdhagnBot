import os
from argparse import Namespace
from io import BytesIO

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageOps

from util import command, text, util

from ..util import get_image_and_user

plugin_dir = os.path.dirname(os.path.abspath(__file__))

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
parser.add_argument(
  "-text", "-文本", metavar="内容", default="阿尼亚喜欢这个",
  help="自定义内容，默认为\"阿尼亚喜欢这个\"")
matcher = (
  command.CommandBuilder("petpet_v2.anya", "阿尼亚", "阿尼亚喜欢")
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
    avatar, _ = await get_image_and_user(bot, event, args.target, event.self_id, crop=False)
  except util.AggregateError as e:
    await matcher.finish("\n".join(e))
  avatar = ImageOps.fit(avatar, (305, 235), util.scale_resample)
  content = args.text
  template = Image.open(os.path.join(plugin_dir, "template.png"))
  height = template.height
  if content:
    height += 40
  im = Image.new("RGB", (template.width, height), (0, 0, 0))
  im.paste(avatar, (106, 72), avatar)
  text.paste(
    im, (im.width // 2, height - 20), content, "sans", 28, color=(255, 255, 255), anchor="mm")
  im.paste(template, mask=template)
  f = BytesIO()
  im.save(f, "png")
  await matcher.send(MessageSegment.image(f))
