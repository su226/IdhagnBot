import random
from argparse import Namespace
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, imutil, misc
from util.misc import range_int
from util.user_aliases import AvatarGetter, DefaultType

DIR = Path(__file__).resolve().parent

parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
parser.add_argument("--template", "-t", type=range_int(0, 91), metavar="编号", help=(
  "使用指定表情包而非随机，编号是 [0, 91] 之间的整数"
))
matcher = (
  command.CommandBuilder("meme_pic.getout", "爬")
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
    template_id = random.randrange(92) if args.template is None else args.template
    im = Image.open(DIR / f"{template_id}.jpg")
    target = target.resize((100, 100), imutil.scale_resample())
    imutil.circle(target)
    im.paste(target, (0, 400), target)
    return imutil.to_segment(im)

  await matcher.finish(await misc.to_thread(make))
