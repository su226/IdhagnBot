import math
import random
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
SCALE = 10
AMPLITUDE = 0.01
_GRAD3 = (
  (1, 1, 0), (-1, 1, 0), (1, -1, 0), (-1, -1, 0),
  (1, 0, 1), (-1, 0, 1), (1, 0, -1), (-1, 0, -1),
  (0, 1, 1), (0, -1, 1), (0, 1, -1), (0, -1, -1),
  (1, 1, 0), (0, -1, 1), (-1, 1, 0), (0, -1, -1),
)
_F2 = 0.5 * (3 ** 0.5 - 1)
_G2 = (3 - 3 ** 0.5) / 6


class PerlinNoise2D:
  # 柏林噪声
  # https://github.com/caseman/noise/blob/master/perlin.py

  def __init__(self):
    permutation = list(range(256))
    random.shuffle(permutation)
    self.permutation = tuple(permutation) * 2

  def __call__(self, x: float, y: float, octaves: int = 1) -> float:
    if octaves > 1:
      freq = 1
      amp = 1
      max = 0
      total = 0
      for i in range(octaves):
        max += amp
        total += self(x * freq, y * freq) * amp
        freq *= 2
        amp *= 0.5
      return total / max

    s = (x + y) * _F2
    i = int(x + s)
    j = int(y + s)
    t = (i + j) * _G2
    x0 = x - (i - t)
    y0 = y - (j - t)

    if x0 > y0:
      i1 = 1
      j1 = 0
    else:
      i1 = 0
      j1 = 1

    x1 = x0 - i1 + _G2
    y1 = y0 - j1 + _G2
    x2 = x0 + _G2 * 2.0 - 1.0
    y2 = y0 + _G2 * 2.0 - 1.0

    perm = self.permutation
    ii = int(i) % 256
    jj = int(j) % 256
    gi0 = perm[ii + perm[jj]] % 12
    gi1 = perm[ii + i1 + perm[jj + j1]] % 12
    gi2 = perm[ii + 1 + perm[jj + 1]] % 12

    tt = 0.5 - x0**2 - y0**2
    if tt > 0:
      g = _GRAD3[gi0]
      noise = tt**4 * (g[0] * x0 + g[1] * y0)
    else:
      noise = 0.0

    tt = 0.5 - x1**2 - y1**2
    if tt > 0:
      g = _GRAD3[gi1]
      noise += tt**4 * (g[0] * x1 + g[1] * y1)

    tt = 0.5 - x2**2 - y2**2
    if tt > 0:
      g = _GRAD3[gi2]
      noise += tt**4 * (g[0] * x2 + g[1] * y2)

    return noise * 70.0


def marble(
  noise: PerlinNoise2D, im: Image.Image, scale: float, amp: float, i: int,
  resample: Image.Resampling
) -> Image.Image:
  im = ImageOps.contain(im, (MAX_SIZE, MAX_SIZE), resample)
  out = Image.new("RGBA", im.size)
  px = im.load()
  out_px = out.load()
  phase = math.tau / FRAMES * i

  for x in range(im.width):
    for y in range(im.height):
      angle = noise(x * scale, y * scale) * math.pi + math.pi
      x1 = round(x + math.sin(angle + phase) * amp)
      y1 = round(y + math.cos(angle + phase) * amp)
      if x1 >= 0 and y1 >= 0 and x1 < im.width and y1 < im.height:
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
  command.CommandBuilder("meme_pic.marble", "大理石")
  .category("meme_pic")
  .brief("[动] 大理石特效")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, DefaultType.TARGET, raw=True)

  def make() -> MessageSegment:
    target, _ = target_task.result()
    im_scale = min(MAX_SIZE / target.width, MAX_SIZE / target.height, 1)
    scale = SCALE / (target.width * im_scale)
    amp = AMPLITUDE * target.width * im_scale
    noise = PerlinNoise2D()
    resample = imutil.scale_resample()

    futures: List[Future[Image.Image]] = []
    with ProcessPoolExecutor() as exec:
      for i, raw in zip(range(FRAMES), imutil.sample_frames(target, FRAMETIME)):
        im = raw.convert("RGBA")
        futures.append(exec.submit(marble, noise, im, scale, amp, i, resample))
    frames: List[Image.Image] = [future.result() for future in futures]

    return imutil.to_segment(frames, FRAMETIME, afmt=args.format)

  await matcher.finish(await misc.to_thread(make))
