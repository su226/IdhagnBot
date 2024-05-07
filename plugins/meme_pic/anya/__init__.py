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


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接（可传入动图）"
))
parser.add_argument("--text", "-t", metavar="内容", default="阿尼亚喜欢这个", help=(
  "自定义内容，默认为“阿尼亚喜欢这个”"
))
group = parser.add_mutually_exclusive_group()
group.add_argument(
  "--webp", "-w", action="store_const", dest="format", const="webp", default="gif",
  help="使用WebP而非GIF格式（如果传入动图）",
)
group.add_argument(
  "--png", "--apng", "-p", action="store_const", dest="format", const="png",
  help="使用APNG而非GIF格式（如果传入动图）",
)
matcher = (
  command.CommandBuilder("meme_pic.anya", "阿尼亚", "阿尼亚喜欢")
  .category("meme_pic")
  .brief("[动]")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, DefaultType.TARGET)

  def make() -> MessageSegment:
    target, _ = target_task.result()
    template = Image.open(DIR / "template.png")
    text_im = textutil.render(
      args.text, "sans", 28, color=(255, 255, 255), stroke=1, stroke_color=(0, 0, 0))
    if text_im.width > (w := template.width - 10):
      text_im = imutil.resize_width(text_im, w)
    template.paste(text_im, (
      (template.width - text_im.width) // 2, template.height - text_im.height - 10,
    ), text_im)
    frames: List[Image.Image] = []
    for raw in imutil.frames(target):
      frame = ImageOps.fit(raw.convert("RGBA"), (305, 235), imutil.scale_resample())
      im = Image.new("RGB", template.size, (0, 0, 0))
      im.paste(frame, (106, 72), frame)
      im.paste(template, mask=template)
      frames.append(im)
    return imutil.to_segment(frames, target, afmt=args.format)

  await matcher.finish(await misc.to_thread(make))
