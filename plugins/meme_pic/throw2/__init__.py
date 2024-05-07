import random
from argparse import Namespace
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, imutil, misc
from util.user_aliases import AvatarGetter, DefaultType

DIR = Path(__file__).resolve().parent
BOXES = [
  [(32, 32, 108, 36)],
  [(32, 32, 122, 36)],
  [],
  [(123, 123, 19, 129)],
  [(185, 185, -50, 200), (33, 33, 289, 70)],
  [(32, 32, 280, 73)],
  [(35, 35, 259, 31)],
  [(175, 175, -50, 220)],
]


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
parser.add_argument("--rotate", "-r", type=float, metavar="角度", help="指定旋转角度而非随机")
group = parser.add_mutually_exclusive_group()
group.add_argument(
  "--webp", "-w", action="store_const", dest="format", const="webp", default="gif",
  help="使用WebP而非GIF格式",
)
group.add_argument(
  "--png", "--apng", "-p", action="store_const", dest="format", const="png",
  help="使用APNG而非GIF格式",
)
matcher = (
  command.CommandBuilder("meme_pic.throw2", "扔2")
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
    degree = random.uniform(0, 360) if args.rotate is None else args.rotate
    target = target.rotate(degree, imutil.resample())
    frames = []
    imutil.circle(target)
    for i in range(8):
      frame = Image.open(DIR / f"{i}.png").convert("RGB")
      for w, h, x, y in BOXES[i]:
        target1 = target.resize((w, h), imutil.scale_resample())
        frame.paste(target1, (x, y), mask=target1)
      frames.append(frame)
    return imutil.to_segment(frames, 100, afmt=args.format)

  await matcher.finish(await misc.to_thread(make))
