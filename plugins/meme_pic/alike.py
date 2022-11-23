from argparse import Namespace

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, imutil, misc, textutil
from util.user_aliases import AvatarGetter

parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
matcher = (
  command.CommandBuilder("meme_pic.alike", "一样")
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
    left_im = textutil.render("你怎么跟", "sans", 24)
    right_im = textutil.render("一样", "sans", 24)
    im = Image.new("RGB", (left_im.width + right_im.width + 120, 110), (255, 255, 255))
    im.paste(left_im, (10, 55 - left_im.height // 2), left_im)
    im.paste(right_im, (left_im.width + 110, 55 - right_im.height // 2), right_im)
    target = target.resize((90, 90), imutil.scale_resample())
    im.paste(target, (left_im.width + 15, 10), target)
    return imutil.to_segment(im)

  await matcher.finish(await misc.to_thread(make))
