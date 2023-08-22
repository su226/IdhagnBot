from argparse import Namespace
from pathlib import Path
from typing import List

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageOps

from util import command, imutil, misc, textutil
from util.user_aliases import AvatarGetter, DefaultType

DIR = Path(__file__).resolve().parent
TEXT_WIDTH = 1170
TEXT_HEIGHT = 210


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
parser.add_argument("--text", "-t", default="朋友\n先看看这个图标再说话", metavar="文本", help=(
  "自定义文本，默认为“朋友 先看看这个图标再说话”"
))
group = parser.add_mutually_exclusive_group()
group.add_argument(
  "--webp", "-w", action="store_const", dest="format", const="webp", default="gif",
  help="使用WebP而非GIF格式（如果传入动图）"
)
group.add_argument(
  "--png", "--apng", "-p", action="store_const", dest="format", const="png",
  help="使用APNG而非GIF格式（如果传入动图）"
)
matcher = (
  command.CommandBuilder("meme_pic.icon", "看图标")
  .brief("[动]")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, DefaultType.TARGET, raw=True)

  def make() -> MessageSegment:
    target, _ = target_task.result()
    template = Image.open(DIR / "template.png")
    text_im = textutil.render(args.text, "sans", 100, align="m")
    text_im = imutil.contain_down(text_im, TEXT_WIDTH, TEXT_HEIGHT)
    imutil.paste(template, text_im, (585, 1038), anchor="mm")
    frames: List[Image.Image] = []
    for raw in imutil.frames(target):
      fg = ImageOps.fit(raw.convert("RGBA"), (515, 515), imutil.scale_resample())
      im = Image.new("RGB", template.size, (255, 255, 255))
      im.paste(fg, (599, 403), fg)
      im.paste(template, mask=template)
      frames.append(im)
    return imutil.to_segment(frames, target, afmt=args.format)

  await matcher.finish(await misc.to_thread(make))
