from argparse import Namespace
import os

from PIL import Image
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.exception import ParserExit
from nonebot.rule import ArgumentParser
from nonebot.params import ShellCommandArgs

from util import command, helper, text
from ..util import segment_animated_image, get_image_and_user

plugin_dir = os.path.dirname(os.path.abspath(__file__))

parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
parser.add_argument("-source", default="", metavar="源", help="也可使用\"滑稽\"")
parser.add_argument("-text", "-文本", default="采访大佬经验", help="默认为\"采访大佬经验\"")
group = parser.add_mutually_exclusive_group()
group.add_argument("-webp", action="store_const", dest="format", const="webp", default="gif", help="使用WebP而非GIF格式")
group.add_argument("-apng", "-png", action="store_const", dest="format", const="png", help="使用APNG而非GIF格式")
matcher = (command.CommandBuilder("petpet_v2.interview", "采访")
  .category("petpet_v2")
  .shell(parser)
  .build())
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace | ParserExit = ShellCommandArgs()):
  if isinstance(args, ParserExit):
    await matcher.finish(args.message)
  try:
    avatar, _ = await get_image_and_user(bot, event, args.target, event.self_id)
    if args.source in ("huaji", "滑稽"):
      avatar2 = Image.open(os.path.join(plugin_dir, "huaji.png"))
    else:
      avatar2, _ = await get_image_and_user(bot, event, args.source, event.user_id)
      avatar2 = avatar2.resize((120, 120), Image.ANTIALIAS)
  except helper.AggregateError as e:
    await matcher.finish("\n".join(e))

  frames: list[Image.Image] = []
  avatar = avatar.resize((120, 120), Image.ANTIALIAS)

  template = Image.new("RGB", (600, 280), (255, 255, 255))
  template.paste(avatar, (50, 50), avatar)

  layout = text.layout(args.text, "sans", 50)
  w, h = layout.get_pixel_size()
  if w > 550 * 2.5:
    await matcher.finish("文本过长")
  text_im = text.render(layout)
  if w > 550:
    text_im = text_im.resize((550, h * 550 // w), Image.ANTIALIAS)
  template.paste(text_im, (300 - text_im.width // 2, 215 - text_im.height // 2), text_im)

  for i in range(5):
    offset = -45 * i
    im = template.copy()
    microphone = Image.open(os.path.join(plugin_dir, "microphone.png"))
    im.paste(avatar2, (430 + offset, 50), avatar2)
    im.paste(microphone, (360 + offset, 100), microphone)
    frames.append(im)

  await matcher.finish(segment_animated_image(args.format, frames, [200, 100, 100, 100, 300]))
