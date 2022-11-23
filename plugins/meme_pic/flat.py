from argparse import Namespace

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, imutil, misc, textutil
from util.misc import range_float
from util.user_aliases import AvatarGetter

WIDTH = 500
TEXT_WIDTH = WIDTH - 20
TEXT_HEIGHT = 80


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
parser.add_argument("--text", "-t", default="可恶…被人看扁了", metavar="文本", help=(
  "自定义内容，默认为“可恶…被人看扁了”"
))
parser.add_argument("--ratio", "-r", type=range_float(1, 10), default=2, metavar="倍数", help=(
  "缩放倍数，默认为2"
))
matcher = (
  command.CommandBuilder("meme_pic.flat", "看扁")
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
    target = target.resize((WIDTH, WIDTH // args.ratio), imutil.scale_resample())
    im = Image.new("RGB", (WIDTH, TEXT_HEIGHT + target.height), (255, 255, 255))
    text_im = textutil.render(args.text, "sans", 55)
    text_im = imutil.contain_down(text_im, TEXT_WIDTH, TEXT_HEIGHT)
    imutil.paste(im, text_im, (im.width // 2, TEXT_HEIGHT // 2), anchor="mm")
    im.paste(target, (0, TEXT_HEIGHT), target)
    return imutil.to_segment(im)

  await matcher.finish(await misc.to_thread(make))
