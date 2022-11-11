import asyncio
from argparse import Namespace
from pathlib import Path

import cairo
import cv2
import numpy as np
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageChops, ImageFilter, ImageOps

from util import command, imutil
from util.misc import range_int
from util.user_aliases import AvatarGetter


def kernel_average(size: int) -> np.ndarray:
  return np.full((size, size), 1 / size ** 2)


DIR = Path(__file__).resolve().parent
KERNELS: dict[str, np.ndarray] = {
  "thin": kernel_average(5),
  "normal": kernel_average(7),
  "semibold": kernel_average(9),
  "bold": kernel_average(11),
  "black": kernel_average(13),
  "emboss": np.array([
    [1, 1, 1],
    [1, 1, -1],
    [-1, -1, -1],
  ]),
}
# 这些选项在原网站不可调
SHADE_LIGHT = 80
LIGHT_CUT = 128


def make_mask(
  im: Image.Image,
  pencil: Image.Image,
  kernel: str = "normal",
  dark_cut: int = 118,  # 对应原网站线迹轻重
  shade_limit: int = 108,  # 对应原网站调子数量
  denoise: bool = True  # 对应原网站降噪
) -> Image.Image:
  shade = im.point(lambda v: 0 if v > shade_limit else 255, "L")
  shade = shade.filter(ImageFilter.BoxBlur(3))
  shade = ImageChops.multiply(shade, ImageChops.invert(pencil))
  shade = ImageChops.multiply(shade, Image.new("L", shade.size, SHADE_LIGHT))

  if denoise:
    im = im.filter(ImageFilter.Kernel((3, 3), [1] * 9, 9))

  # 因为PIL只支持3x3和5x5的卷积核，NumPy的卷积是一维的，要用OpenCV
  im1 = Image.fromarray(cv2.filter2D(np.array(im), -1, KERNELS[kernel]))
  im = ImageChops.subtract(im, im1, 1, 128)

  scale = (255 - LIGHT_CUT - dark_cut) / 255
  im = ImageChops.subtract(im, Image.new("L", im.size, dark_cut), scale)

  return ImageChops.lighter(ImageChops.invert(im), shade)


def make_gradient(width: int, height: int) -> Image.Image:
  with cairo.ImageSurface(cairo.FORMAT_RGB24, width, height) as surface:
    cr = cairo.Context(surface)
    gradient = cairo.LinearGradient(0, 0, width, height)
    gradient.add_color_stop_rgb(0.0, 0.984313725490196, 0.7294117647058823, 0.18823529411764706)
    gradient.add_color_stop_rgb(0.4, 0.9882352941176471, 0.4470588235294118, 0.20784313725490197)
    gradient.add_color_stop_rgb(0.6, 0.9882352941176471, 0.20784313725490197, 0.3058823529411765)
    gradient.add_color_stop_rgb(0.7, 0.8117647058823529, 0.21176470588235294, 0.8745098039215686)
    gradient.add_color_stop_rgb(0.8, 0.21568627450980393, 0.7098039215686275, 0.8509803921568627)
    gradient.add_color_stop_rgb(1.0, 0.24313725490196078, 0.7137254901960784, 0.8549019607843137)
    cr.set_source(gradient)
    cr.rectangle(0, 0, width, height)
    cr.fill()
    return imutil.from_cairo(surface)


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接（可传入动图）"
))
parser.add_argument("--style", "-s", choices=list(KERNELS), default="normal", help=(
  "线条风格，可用: thin (精细)、normal (一般)、semibold (稍粗)、bold (超粗)、black (极粗)、"
  "emboss (浮雕)，默认: normal"
))
parser.add_argument("--edge", "-e", type=range_int(80, 126), default=118, metavar="强度", help=(
  "边缘强度，为 [80, 126] 之间的整数，默认: 118"
))
parser.add_argument("--shade", "-a", type=range_int(20, 200), default=108, metavar="强度", help=(
  "暗部强度，为 [20, 200] 之间的整数，默认: 108"
))
parser.add_argument("--no-denoise", "-D", action="store_false", dest="denoise", help="不进行降噪")
group = parser.add_mutually_exclusive_group()
group.add_argument(
  "--webp", "-w", action="store_const", dest="format", const="webp", default="gif",
  help="使用WebP而非GIF格式（如果传入动图）"
)
group.add_argument(
  "--png", "--apng", "-p", action="store_const", dest="format", const="png",
  help="使用APNG而非GIF格式（如果传入动图）"
)
parser.epilog = "特别感谢: https://lab.magiconch.com/one-last-image/"
matcher = (
  command.CommandBuilder("meme_pic.louvre", "卢浮宫")
  .category("meme_pic")
  .brief("[动]")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, event.self_id, raw=True)

  def make() -> MessageSegment:
    target, _ = target_task.result()
    pencil = Image.open(DIR / "pencil.jpg").convert("L")
    pencil = ImageOps.fit(pencil, target.size, imutil.scale_resample())
    gradient = make_gradient(target.width, target.height)
    frames: list[Image.Image] = []
    for raw in imutil.frames(target):
      l, a = raw.convert("LA").split()
      frame = Image.new("L", l.size, 255)
      frame.paste(l, mask=a)
      mask = make_mask(frame, pencil, args.style, args.edge, args.shade, args.denoise)
      frame = Image.new("RGB", l.size, (255, 255, 255))
      frame.paste(gradient, mask=mask)
      frames.append(frame)
    return imutil.to_segment(frames, target, afmt=args.format)

  await matcher.finish(await asyncio.to_thread(make))
