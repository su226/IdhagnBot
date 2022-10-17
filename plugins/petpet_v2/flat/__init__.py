import asyncio
from argparse import Namespace
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, text, util

from ..util import get_image_and_user

DIR = Path(__file__).resolve().parent
WIDTH = 500
TEXT_WIDTH = WIDTH - 20
TEXT_HEIGHT = 80

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标",
  help="可使用@、QQ号、昵称、群名片或图片链接"
)
parser.add_argument(
  "--text", "-t", default="可恶…被人看扁了", metavar="文本",
  help="默认为“可恶…被人看扁了”"
)
parser.add_argument(
  "--ratio", "-r", type=float, default=2,
  help="缩放倍数，默认为2"
)

matcher = command.CommandBuilder("petpet_v2.flat", "看扁") \
  .category("petpet_v2") \
  .shell(parser) \
  .auto_reject() \
  .build()
@matcher.handle()
async def handler(
  bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()
) -> None:
  try:
    target, _ = await get_image_and_user(bot, event, args.target, event.self_id, crop=False)
  except util.AggregateError as e:
    await matcher.finish("\n".join(e))

  def make() -> MessageSegment:
    nonlocal target
    target = target.resize((WIDTH, WIDTH // args.ratio), util.scale_resample)
    im = Image.new("RGB", (WIDTH, TEXT_HEIGHT + target.height), (255, 255, 255))
    text_im = text.render(args.text, "sans", 55)
    text_im = util.contain_down(text_im, TEXT_WIDTH, TEXT_HEIGHT)
    util.paste(im, text_im, (im.width // 2, TEXT_HEIGHT // 2), anchor="mm")
    im.paste(target, (0, TEXT_HEIGHT), target)
    return util.pil_image(im)

  await matcher.finish(await asyncio.to_thread(make))
