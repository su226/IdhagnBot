import math
from argparse import Namespace
from concurrent.futures import Future, ProcessPoolExecutor
from typing import List

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageOps

from util import command, imutil, misc
from util.user_aliases import AvatarGetter, DefaultType

FRAMES = 8
FRAMETIME = 50
MAX_SIZE = 720
FREQUENCY = 40
AMPLITUDE = 120


def wave(
  im: Image.Image, freq: float, amp: float, i: int, resample: Image.Resampling
) -> Image.Image:
  im = ImageOps.contain(im.convert("RGBA"), (MAX_SIZE, MAX_SIZE), resample)
  out = Image.new("RGBA", im.size)
  px = im.load()
  out_px = out.load()
  phase = math.tau / FRAMES * i

  for x in range(im.width):
    for y in range(im.height):
      r = y / im.height
      x1 = x + int(math.sin(freq * x + phase) * amp * (1 - r))
      y1 = y + int(math.sin(freq * y + phase) * amp * r)
      if 0 <= x1 < im.width and 0 <= y1 < im.height:
        out_px[x, y] = px[x1, y1]

  return out


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
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
  command.CommandBuilder("meme_pic.wave", "波纹")
  .category("meme_pic")
  .brief("[动]")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, DefaultType.TARGET, raw=True)

  def make() -> MessageSegment:
    target, _ = target_task.result()
    scale = min(MAX_SIZE / target.width, MAX_SIZE / target.height, 1)
    freq = FREQUENCY / (scale * target.width)
    amp = scale * target.width / AMPLITUDE
    resample = imutil.scale_resample()

    futures: List[Future[Image.Image]] = []
    with ProcessPoolExecutor() as exec:
      for i, raw in zip(range(FRAMES), imutil.sample_frames(target, FRAMETIME)):
        im = raw.convert("RGBA")
        futures.append(exec.submit(wave, im, freq, amp, i, resample))
    frames: List[Image.Image] = [future.result() for future in futures]

    return imutil.to_segment(frames, FRAMETIME, afmt=args.format)

  await matcher.finish(await misc.to_thread(make))
