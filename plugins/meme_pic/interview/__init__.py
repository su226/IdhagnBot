from argparse import Namespace
from pathlib import Path
from typing import Any, List

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
parser.add_argument("--source", "-s", default="", metavar="源", help=(
  "默认为“滑稽”，也可使用@、QQ号、昵称、群名片或图片链接"
))
parser.add_argument("--text", "-t", default="采访大佬经验", metavar="文本", help=(
  "自定义文本，默认为“采访大佬经验”"
))
group = parser.add_mutually_exclusive_group()
group.add_argument(
  "--webp", "-w", action="store_const", dest="format", const="webp", default="gif",
  help="使用WebP而非GIF格式"
)
group.add_argument(
  "--png", "--apng", "-p", action="store_const", dest="format", const="png",
  help="使用APNG而非GIF格式"
)
matcher = (
  command.CommandBuilder("meme_pic.interview", "采访")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, DefaultType.TARGET, "目标")
    source_task = Any
    if args.source not in ("", "huaji", "滑稽"):
      source_task = g(args.source, DefaultType.SOURCE, "源")

  def make() -> MessageSegment:
    target, _ = target_task.result()
    target = target.resize((120, 120), imutil.scale_resample())
    if args.source in ("", "huaji", "滑稽"):
      source = Image.open(DIR / "huaji.png")
    else:
      source, _ = source_task.result()
      source = source.resize((120, 120), imutil.scale_resample())

    template = Image.new("RGB", (600, 280), (255, 255, 255))
    template.paste(target, (50, 50), target)

    layout = textutil.layout(args.text, "sans", 50)
    text_im = textutil.render(layout)
    text_im = imutil.contain_down(text_im, 550, 100)
    imutil.paste(template, text_im, (300, 215), anchor="mm")

    frames: List[Image.Image] = []
    for i in range(5):
      offset = -45 * i
      im = template.copy()
      microphone = Image.open(DIR / "microphone.png")
      im.paste(source, (430 + offset, 50), source)
      im.paste(microphone, (360 + offset, 100), microphone)
      frames.append(im)

    return imutil.to_segment(frames, [200, 100, 100, 100, 300], afmt=args.format)

  await matcher.finish(await misc.to_thread(make))
