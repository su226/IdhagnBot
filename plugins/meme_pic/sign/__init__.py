import asyncio
from argparse import Namespace
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageOps

from util import command, imutil
from util.user_aliases import AvatarGetter

DIR = Path(__file__).resolve().parent
FRAMETIME = 200
# TRANSFORMS = [                                                                          # noqa
#   (RemapTransform((315, 210), ((0, 46), (320, 0), (350, 214), (38, 260))), (68, 91)),   # noqa
#   (RemapTransform((315, 210), ((18, 0), (328, 28), (298, 227), (0, 197))), (184, 77)),  # noqa
#   (RemapTransform((315, 210), ((15, 0), (294, 28), (278, 216), (0, 188))), (194, 65)),  # noqa
#   (RemapTransform((315, 210), ((14, 0), (279, 27), (262, 205), (0, 178))), (203, 55)),  # noqa
#   (RemapTransform((315, 210), ((14, 0), (270, 25), (252, 195), (0, 170))), (209, 49)),  # noqa
#   (RemapTransform((315, 210), ((15, 0), (260, 25), (242, 186), (0, 164))), (215, 41)),  # noqa
#   (RemapTransform((315, 210), ((10, 0), (245, 21), (230, 180), (0, 157))), (223, 35)),  # noqa
#   (RemapTransform((315, 210), ((13, 0), (230, 21), (218, 168), (0, 147))), (231, 25)),  # noqa
#   (RemapTransform((315, 210), ((13, 0), (220, 23), (210, 167), (0, 140))), (238, 21)),  # noqa
#   (RemapTransform((315, 210), ((27, 0), (226, 46), (196, 182), (0, 135))), (254, 13)),  # noqa
#   (RemapTransform((315, 210), ((27, 0), (226, 46), (196, 182), (0, 135))), (254, 13)),  # noqa
#   (RemapTransform((315, 210), ((27, 0), (226, 46), (196, 182), (0, 135))), (254, 13)),  # noqa
#   (RemapTransform((315, 210), ((0, 35), (200, 0), (224, 133), (25, 169))), (175, 9)),   # noqa
#   (RemapTransform((315, 210), ((0, 35), (200, 0), (224, 133), (25, 169))), (195, 17)),  # noqa
#   (RemapTransform((315, 210), ((0, 35), (200, 0), (224, 133), (25, 169))), (195, 17)),  # noqa
# ]                                                                                       # noqa
OLD_SIZE = (315, 210)
TRANSFORMS = [
  ((68, 91), (350, 260), (
    0.9499655048854788, -0.16868546348434382, 7.759531320277863, 0.13351315361055088,
    0.9287871555516278, -42.72420915537515, -3.225701504332547e-05, -0.00010821681125833889
  )),
  ((184, 77), (328, 227), (
    1.025339174073316, 0.09368581285949365, -18.456105133320595, -0.0920531600966951,
    1.019159986784861, 1.6569568817397045, 6.864054431940836e-05, -0.0001829472013933449
  )),
  ((194, 65), (294, 216), (
    1.1207222384724669, 0.08941932753770233, -16.810833577083933, -0.11082302025279593,
    1.1042722375189358, 1.6623453037918845, 3.7720584324352994e-06, -1.860369915524315e-05
  )),
  ((203, 55), (279, 205), (
    1.1814730836380778, 0.09292484927490864, -16.540623170932125, -0.11793211151157368,
    1.157481835206188, 1.6510495611614036, 1.281859807821385e-05, -6.198993504914611e-05
  )),
  ((209, 49), (270, 195), (
    1.22378287671452, 0.1007821192588335, -17.132960274003334, -0.11785036688406189,
    1.206787756892787, 1.6499051363765975, 1.778963299513801e-05, -8.952874486975877e-05
  )),
  ((215, 41), (260, 186), (
    1.2517205556558098, 0.11448663618803862, -18.775808334836544, -0.1275995657203717,
    1.250475744059605, 1.9139934858056096, -5.834550217864536e-05, -8.733985158010171e-05
  )),
  ((223, 35), (245, 180), (
    1.354991328975779, 0.08630518018953255, -13.549913289756578, -0.11653031707332509,
    1.3040297386777286, 1.1653031707329438, 7.850196852941132e-05, -0.00012441698079659793
  )),
  ((231, 25), (230, 168), (
    1.4382485129346099, 0.12719204536156278, -18.697230668148787, -0.13769179567705112,
    1.422815221996149, 1.7899933438022253, -5.952922508195525e-06, 3.057437567979631e-05
  )),
  ((238, 21), (220, 167), (
    1.5468295366139606, 0.14363417125702094, -20.108783975984952, -0.16779598025159465,
    1.5101638222643337, 2.181347743271007, 0.00010979944793242048, 0.00012259465511148596
  )),
  ((254, 13), (226, 182), (
    1.5346759021461736, 0.30693518042923923, -41.43624935794438, -0.33985449289452724,
    1.4702400888263283, 9.17607130815283, 8.029636225883176e-05, -8.259318166817329e-05
  )),
  ((254, 13), (226, 182), (
    1.5346759021461736, 0.30693518042923923, -41.43624935794438, -0.33985449289452724,
    1.4702400888263283, 9.17607130815283, 8.029636225883176e-05, -8.259318166817329e-05
  )),
  ((254, 13), (226, 182), (
    1.5346759021461736, 0.30693518042923923, -41.43624935794438, -0.33985449289452724,
    1.4702400888263283, 9.17607130815283, 8.029636225883176e-05, -8.259318166817329e-05
  )),
  ((175, 9), (224, 169), (
    1.5110899442465142, -0.2819197657176347, 9.867191800112934, 0.26433334223714766,
    1.5104762413551394, -52.866668447429404, -4.626697381877377e-05, -2.0990377287486003e-05
  )),
  ((195, 17), (224, 169), (
    1.5110899442465142, -0.2819197657176347, 9.867191800112934, 0.26433334223714766,
    1.5104762413551394, -52.866668447429404, -4.626697381877377e-05, -2.0990377287486003e-05
  )),
  ((195, 17), (224, 169), (
    1.5110899442465142, -0.2819197657176347, 9.867191800112934, 0.26433334223714766,
    1.5104762413551394, -52.866668447429404, -4.626697381877377e-05, -2.0990377287486003e-05
  )),
]


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
  command.CommandBuilder("meme_pic.sign", "举牌")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, event.self_id, crop=False)

  def make() -> MessageSegment:
    target, _ = target_task.result()
    target = ImageOps.pad(target, OLD_SIZE, imutil.scale_resample())
    frames: list[Image.Image] = []
    for i, transform in enumerate(TRANSFORMS):
      pos, size, data = transform
      template = Image.open(DIR / f"{i}.png").convert("RGBA")
      im = Image.new("RGB", template.size, (249, 249, 249))
      fg = target.transform(size, Image.Transform.PERSPECTIVE, data, imutil.resample())
      im.paste(fg, pos, fg)
      im.paste(template, mask=template)
      frames.append(im)
    return imutil.to_segment(frames, FRAMETIME, afmt=args.format)

  await matcher.finish(await asyncio.to_thread(make))