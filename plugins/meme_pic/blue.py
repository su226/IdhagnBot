from argparse import Namespace

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser

from util import command, imutil, misc, textutil
from util.user_aliases import AvatarGetter, DefaultType

COLOR = (78, 114, 184)


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
matcher = (
  command.CommandBuilder("meme_pic.blue", "群青")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, DefaultType.TARGET, bg=(191, 191, 191))

  def make() -> MessageSegment:
    target, _ = target_task.result()
    im = target.resize((500, 500), imutil.scale_resample()).convert("L")
    im = imutil.colorize(im, "black", "white", COLOR)
    textutil.paste(
      im, (400, 50), "群", "sans bold", 80,
      color=(255, 255, 255), stroke=2, stroke_color=COLOR,
    )
    textutil.paste(
      im, (400, 150), "青", "sans bold", 80,
      color=(255, 255, 255), stroke=2, stroke_color=COLOR,
    )
    textutil.paste(
      im, (310, 270), "YOASOBI", "sans bold", 40,
      color=(255, 255, 255), stroke=2, stroke_color=COLOR,
    )
    return imutil.to_segment(im)

  await matcher.finish(await misc.to_thread(make))
