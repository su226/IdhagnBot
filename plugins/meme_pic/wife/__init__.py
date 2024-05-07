from argparse import Namespace
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, imutil, misc, textutil
from util.user_aliases import AvatarGetter, DefaultType

DIR = Path(__file__).resolve().parent


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
matcher = (
  command.CommandBuilder("meme_pic.wife", "这是我的老婆", "老婆")
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
    target = imutil.resize_width(target, 400)
    im = Image.new("RGB", (650, target.height + 500), (255, 255, 255))
    im.paste(target, (325 - target.width // 2, 105), target)

    textutil.paste(
      im, (325, 51),
      "如果你的老婆长这样", "sans bold", 64, anchor="mm",
    )
    textutil.paste(
      im, (325, target.height + 188),
      "那么这就不是你的老婆\n这是我的老婆", "sans bold", 48, align="m", anchor="mm",
    )
    textutil.paste(
      im, (214, target.height + 363),
      "滚去找你\n自己的老婆去", "sans bold", 64, align="m", anchor="mm",
    )

    template = Image.open(DIR / "template.png").resize((200, 200), imutil.scale_resample())
    im.paste(template, (421, target.height + 270))
    return imutil.to_segment(im)

  await matcher.finish(await misc.to_thread(make))
