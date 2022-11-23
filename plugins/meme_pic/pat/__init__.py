from argparse import Namespace
from pathlib import Path
from typing import List

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, imutil, misc
from util.user_aliases import AvatarGetter

DIR = Path(__file__).resolve().parent
FRAME_ORDER = [0, 1, 2, 3, 1, 2, 3, 0, 1, 2, 3, 0, 0, 1, 2, 3, 0, 0, 0, 0, 4, 5, 5, 5, 6, 7, 8, 9]
BOXES = [(11, 73, 106, 100), (8, 79, 112, 96)]


parser = ArgumentParser(add_help=False, epilog="~~你TM拍我瓜是吧~~")
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
group = parser.add_mutually_exclusive_group()
group.add_argument(
  "--webp", "-w", action="store_const", dest="format", const="webp", default="gif",
  help="使用WebP而非GIF格式")
group.add_argument(
  "--png", "--apng", "-p", action="store_const", dest="format", const="png",
  help="使用APNG而非GIF格式"
)
matcher = (
  command.CommandBuilder("meme_pic.pat", "拍拍", "拍")
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
    frames: List[Image.Image] = []
    for i in range(10):
      frame = Image.new("RGBA", (235, 196), (255, 255, 255, 0))
      x, y, w, h = BOXES[1 if i == 2 else 0]
      frame.paste(target.resize((w, h), imutil.scale_resample()), (x, y))
      raw_frame = Image.open(DIR / f"{i}.png").convert("RGBA")
      frame.paste(raw_frame, mask=raw_frame)
      frames.append(frame)
    frames = [frames[n] for n in FRAME_ORDER]
    return imutil.to_segment(frames, 85, afmt=args.format)

  await matcher.finish(await misc.to_thread(make))
