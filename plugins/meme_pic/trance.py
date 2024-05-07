from argparse import Namespace

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, imutil, misc
from util.user_aliases import AvatarGetter, DefaultType

parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
matcher = (
  command.CommandBuilder("meme_pic.trance", "恍惚")
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
    im = Image.new("RGB", target.size, (255, 255, 255))
    im.paste(target, mask=target)
    target = im.copy()
    alpha = Image.new("L", im.size, 3)
    for i in range(0, int(im.height * -0.1), -1):
      im.paste(target, (0, i), alpha)
    for i in range(int(im.height * 0.1)):
      im.paste(target, (0, i), alpha)
    return imutil.to_segment(im)

  await matcher.finish(await misc.to_thread(make))
