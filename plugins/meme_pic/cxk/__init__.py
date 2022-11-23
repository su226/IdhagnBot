import random
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
parser.add_argument("--source", "-s", default="", metavar="源", help="同上")
matcher = (
  command.CommandBuilder("meme_pic.cxk", "cxk", "蔡徐坤", "篮球", "jntm", "鸡你太美")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, event.self_id, "目标")
    source_task = g(args.source, event.user_id, "源")

  def make() -> MessageSegment:
    target, _ = target_task.result()
    source, _ = source_task.result()
    target = target.resize((130, 130), imutil.scale_resample())
    target = target.rotate(random.uniform(0, 360), imutil.resample())
    source = source.resize((130, 130), imutil.scale_resample())
    im = Image.new("RGB", (830, 830), (255, 255, 255))
    im.paste(source, (382, 59), source)
    im.paste(target, (609, 317), target)
    template = Image.open(DIR / "template.png")
    im.paste(template, mask=template)
    return imutil.to_segment(im)

  await matcher.finish(await misc.to_thread(make))
