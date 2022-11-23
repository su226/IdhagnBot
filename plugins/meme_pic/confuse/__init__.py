from argparse import Namespace
from pathlib import Path
from typing import List

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageOps

from util import command, imutil, misc
from util.user_aliases import AvatarGetter

DIR = Path(__file__).resolve().parent
FRAMETIME = 15


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接（可传入动图）"
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
  command.CommandBuilder("meme_pic.confuse", "迷惑", "疑惑")
  .brief("[动]")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, event.self_id, raw=True)

  def make() -> MessageSegment:
    target, _ = target_task.result()
    frames: List[Image.Image] = []
    for i, raw in zip(range(100), imutil.sample_frames(target, FRAMETIME)):
      template = Image.open(DIR / f"{i}.png").convert("RGBA")
      fg = ImageOps.contain(raw.convert("RGBA"), template.size, imutil.scale_resample())
      x = (template.width - fg.width) // 2
      y = (template.height - fg.height) // 2
      template = template.crop((x, y, x + fg.width, y + fg.height))
      im = Image.new("RGB", fg.size, (255, 255, 255))
      im.paste(fg, mask=fg)
      im.paste(template, mask=template)
      frames.append(im)
    return imutil.to_segment(frames, FRAMETIME, afmt=args.format)

  await matcher.finish(await misc.to_thread(make))
