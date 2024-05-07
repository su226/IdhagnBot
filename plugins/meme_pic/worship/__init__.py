from argparse import Namespace
from pathlib import Path
from typing import List

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, imutil, misc
from util.user_aliases import AvatarGetter, DefaultType

DIR = Path(__file__).resolve().parent
# RemapTransform((150, 150), ((0, -30), (135, 17), (135, 145), (0, 140)))  # noqa: ERA001
OLD_SIZE = (150, 150)
NEW_SIZE = (135, 145)
TRANSFORM = (
  0.8366013071895618, 1.2128331252511345e-14, -3.561263629370086e-12, -0.3071895424836637,
  0.8823529411764716, 26.47058823529454, -0.0018300653594771486, 3.1736140776801494e-17,
)


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
group = parser.add_mutually_exclusive_group()
group.add_argument(
  "--webp", "-w", action="store_const", dest="format", const="webp", default="gif",
  help="使用WebP而非GIF格式",
)
group.add_argument(
  "--png", "--apng", "-p", action="store_const", dest="format", const="png",
  help="使用APNG而非GIF格式",
)
matcher = (
  command.CommandBuilder("meme_pic.worship", "膜拜")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, DefaultType.TARGET)

  def make() -> MessageSegment:
    target, _ = target_task.result()
    frames: List[Image.Image] = []
    target = target.resize(OLD_SIZE, imutil.scale_resample()).transform(
      NEW_SIZE, Image.Transform.PERSPECTIVE, TRANSFORM, imutil.resample(),
    )
    for i in range(10):
      template = Image.open(DIR / f"{i}.png")
      im = Image.new("RGB", template.size, (255, 255, 255))
      im.paste(target, mask=target)
      im.paste(template, mask=template)
      frames.append(im)
    return imutil.to_segment(frames, 40, afmt=args.format)

  await matcher.finish(await misc.to_thread(make))
