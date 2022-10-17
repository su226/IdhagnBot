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
# RemapTransform((150, 150), ((0, 20), (154, 0), (164, 153), (22, 180)))  # noqa
OLD_SIZE = (150, 150)
NEW_SIZE = (164, 180)
TRANSFORM = (
  0.8955540939219657, -0.1231386879142573, 2.4627737582811897, 0.10983370584176559,
  0.8457195349815885, -16.91439069963202, -0.0004165322847504612, -0.0004034806049907501
)

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标",
  help="可使用@、QQ号、昵称、群名片或图片链接"
)
parser.add_argument(
  "--text", "-t", default="你刚才说的话不是很礼貌！", metavar="文本",
  help="默认为“你刚才说的话不是很礼貌！”"
)

matcher = command.CommandBuilder("petpet_v2.impolite", "不文明", "不礼貌") \
  .category("petpet_v2") \
  .shell(parser) \
  .auto_reject() \
  .build()
@matcher.handle()
async def handler(
  bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()
) -> None:
  try:
    target, _ = await get_image_and_user(bot, event, args.target, event.self_id)
  except util.AggregateError as e:
    await matcher.finish("\n".join(e))

  def make() -> MessageSegment:
    nonlocal target
    im = Image.open(DIR / "template.png")
    target = target.resize(OLD_SIZE, util.scale_resample)
    util.circle(target)
    target = target.transform(NEW_SIZE, Image.Transform.PERSPECTIVE, TRANSFORM, util.resample)
    im.paste(target, (137, 151), target)

    text_im = text.render(args.text, "serif", 50)
    text_im = util.contain_down(text_im, 471, 75)
    util.paste(im, text_im, (293, 80), anchor="mm")

    return util.pil_image(im)

  await matcher.finish(await asyncio.to_thread(make))
