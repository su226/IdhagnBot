import os
from argparse import Namespace
from io import BytesIO

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageDraw, ImageOps

from util import command, helper, resources

from ..util import get_image_and_user

plugin_dir = os.path.dirname(os.path.abspath(__file__))
COLOR = (78, 114, 184)

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
matcher = (
  command.CommandBuilder("petpet_v2.blue", "群青")
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
  avatar = avatar.resize((500, 500), Image.ANTIALIAS).convert("LA")  # type: ignore
  im = Image.new("L", (500, 500), 191)
  im.paste(avatar, mask=avatar.getchannel("A"))
  im = ImageOps.colorize(im, (0, 0, 0), (255, 255, 255), COLOR)  # type: ignore
  draw = ImageDraw.Draw(im)
  font = resources.font("sans-bold", 80)
  draw.text((400, 50), "群", (255, 255, 255), font, stroke_width=2, stroke_fill=COLOR)
  draw.text((400, 150), "青", (255, 255, 255), font, stroke_width=2, stroke_fill=COLOR)
  font = resources.font("sans-bold", 40)
  draw.text((310, 270), "YOASOBI", (255, 255, 255), font, stroke_width=2, stroke_fill=COLOR)
  f = BytesIO()
  im.save(f, "PNG")
  await matcher.finish(MessageSegment.image(f))
