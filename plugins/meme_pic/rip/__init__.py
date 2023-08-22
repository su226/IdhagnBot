from argparse import Namespace
from pathlib import Path
from typing import Any

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, imutil, misc
from util.user_aliases import AvatarGetter, DefaultType

DIR = Path(__file__).resolve().parent


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
parser.add_argument("--source", "-s", default="", metavar="源", help=(
  "除了@、QQ号、昵称、群名片或图片链接，也可使用“滑稽”或者“熊猫头”"
))
matcher = (
  command.CommandBuilder("meme_pic.rip", "撕")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, DefaultType.TARGET, "目标")
    source_task = Any
    if args.source not in ("huaji", "滑稽", "panda", "熊猫", "熊猫头"):
      source_task = g(args.source, DefaultType.SOURCE, "源")

  def make() -> MessageSegment:
    if args.source in ("huaji", "滑稽"):
      template = Image.open(DIR / "template_huaji.png")
    elif args.source in ("panda", "熊猫", "熊猫头"):
      template = Image.open(DIR / "template_panda.png")
    else:
      source, _ = source_task.result()
      template = Image.new("RGBA", (1080, 804))
      source = source.resize((230, 230), imutil.scale_resample())
      template.paste(source, (408, 418), source)
      template2 = Image.open(DIR / "template_custom.png")
      template.paste(template2, mask=template2)

    target, _ = target_task.result()
    target = target.resize((385, 385), imutil.scale_resample())
    im = Image.new("RGB", template.size, (255, 255, 255))
    left = target.rotate(24, imutil.resample(), True)
    im.paste(left, (-5, 355), left)
    right = target.rotate(-11, imutil.resample(), True)
    im.paste(right, (649, 310), right)
    im.paste(template, mask=template)
    return imutil.to_segment(im)

  await matcher.finish(await misc.to_thread(make))
