from argparse import Namespace
from io import BytesIO
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, text, util

from ..util import get_image_and_user

plugin_dir = Path(__file__).resolve().parent

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
matcher = (
  command.CommandBuilder("petpet_v2.wife", "这是我的老婆", "老婆")
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

  avatar = util.resize_width(avatar, 400)
  im = Image.new("RGB", (650, avatar.height + 500), (255, 255, 255))
  im.paste(avatar, (325 - avatar.width // 2, 105), avatar)

  text.paste(
    im, (325, 51),
    "如果你的老婆长这样", "sans bold", 64, anchor="mm")
  text.paste(
    im, (325, avatar.height + 188),
    "那么这就不是你的老婆\n这是我的老婆", "sans bold", 48, align="m", anchor="mm")
  text.paste(
    im, (214, avatar.height + 363),
    "滚去找你\n自己的老婆去", "sans bold", 64, align="m", anchor="mm")

  template = Image.open(plugin_dir / "template.png").resize((200, 200), util.scale_resample)
  im.paste(template, (421, avatar.height + 270))

  f = BytesIO()
  im.save(f, "PNG")
  await matcher.finish(MessageSegment.image(f))
