from argparse import Namespace
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageOps

from util import command, imutil, misc
from util.user_aliases import AvatarGetter, DefaultType

DIR = Path(__file__).resolve().parent


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
matcher = (
  command.CommandBuilder("meme_pic.work", "打工")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, DefaultType.TARGET, crop=False)

  def make() -> MessageSegment:
    target, _ = target_task.result()
    target = ImageOps.fit(target, (220, 310), imutil.scale_resample())
    target = target.rotate(25, imutil.resample(), True)
    template = Image.open(DIR / "template.png")
    im = Image.new("RGB", template.size, (255, 255, 255))
    im.paste(target, (56, 32), target)
    im.paste(template, mask=template)
    return imutil.to_segment(im)

  await matcher.finish(await misc.to_thread(make))
