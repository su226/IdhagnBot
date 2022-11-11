import asyncio
from argparse import Namespace
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, imutil
from util.user_aliases import AvatarGetter

DIR = Path(__file__).resolve().parent
# RemapTransform((450, 450), ((15, 11), (448, 0), (445, 452), (0, 461)))  # noqa
OLD_SIZE = 450, 450
NEW_SIZE = 448, 461
TRANSFORM = (
  1.0462493084523434, 0.03487497694841008, -16.077364373214344, 0.026154227716037853,
  1.029525509185637, -11.717094016783891, 1.3106774868236476e-05, 6.215553491345412e-05)


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
matcher = (
  command.CommandBuilder("meme_pic.cover", "捂脸")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, event.self_id)

  def make() -> MessageSegment:
    target, _ = target_task.result()
    template = Image.open(DIR / "template.png")
    im = Image.new("RGB", template.size, (255, 255, 255))
    target = target.resize(OLD_SIZE, imutil.scale_resample())
    target = target.transform(NEW_SIZE, Image.Transform.PERSPECTIVE, TRANSFORM, imutil.resample())
    im.paste(target, (120, 154), target)
    im.paste(template, mask=template)
    return imutil.to_segment(im)

  await matcher.finish(await asyncio.to_thread(make))
