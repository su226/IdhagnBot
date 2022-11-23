from argparse import Namespace
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, imutil, misc
from util.user_aliases import AvatarGetter

DIR = Path(__file__).resolve().parent


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
matcher = (
  command.CommandBuilder("meme_pic.watermelon", "劈瓜", "劈", "刘华强", "华强")
  .category("meme_pic")
  .brief("你他喵劈我瓜是吧")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, event.self_id)

  def make() -> MessageSegment:
    target, _ = target_task.result()
    target = target.resize((548, 548), imutil.scale_resample())
    im = Image.new("RGB", (1440, 782), (255, 255, 255))
    im.paste(target, (401, 183), target)
    template = Image.open(DIR / "template.png")
    im.paste(template, mask=template)
    return imutil.to_segment(im)

  await matcher.finish(await misc.to_thread(make))
