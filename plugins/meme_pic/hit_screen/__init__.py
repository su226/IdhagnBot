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
# TRANSFORMS = [                                                                         # noqa
#   (RemapTransform((140, 120), ((1, 10), (138, 1), (140, 119), (7, 154))), (32, 37)),   # noqa
#   (RemapTransform((140, 120), ((1, 10), (138, 1), (140, 121), (7, 154))), (32, 37)),   # noqa
#   (RemapTransform((140, 120), ((1, 10), (138, 1), (139, 125), (10, 159))), (32, 37)),  # noqa
#   (RemapTransform((140, 120), ((1, 12), (136, 1), (137, 125), (8, 159))), (34, 37)),   # noqa
#   (RemapTransform((140, 120), ((1, 9), (137, 1), (139, 122), (9, 154))), (35, 41)),    # noqa
#   (RemapTransform((140, 120), ((1, 8), (144, 1), (144, 123), (12, 155))), (30, 45)),   # noqa
#   (RemapTransform((140, 120), ((1, 8), (140, 1), (141, 121), (10, 155))), (29, 49)),   # noqa
#   (RemapTransform((140, 120), ((1, 9), (140, 1), (139, 118), (10, 153))), (27, 53)),   # noqa
#   (RemapTransform((140, 120), ((1, 7), (144, 1), (145, 117), (13, 153))), (19, 57)),   # noqa
#   (RemapTransform((140, 120), ((1, 7), (144, 1), (143, 116), (13, 153))), (19, 57)),   # noqa
#   (RemapTransform((140, 120), ((1, 8), (139, 1), (141, 119), (12, 154))), (19, 55)),   # noqa
#   (RemapTransform((140, 120), ((1, 13), (140, 1), (143, 117), (12, 156))), (16, 57)),  # noqa
#   (RemapTransform((140, 120), ((1, 10), (138, 1), (142, 117), (11, 149))), (14, 61)),  # noqa
#   (RemapTransform((140, 120), ((1, 10), (141, 1), (148, 125), (13, 153))), (11, 57)),  # noqa
#   (RemapTransform((140, 120), ((1, 12), (141, 1), (147, 130), (16, 150))), (11, 60)),  # noqa
#   (RemapTransform((140, 120), ((1, 15), (165, 1), (175, 135), (1, 171))), (-6, 46)),   # noqa
# ]                                                                                      # noqa
TRANSFORMS = [
  ((32, 37), (140, 154), (
    0.8275793370804023, -0.03448247237833776, -0.48275461329860486, 0.05304045151919573,
    0.8073935397921741, -8.126975849441083, -0.001360976309520633, -0.0001230447760180759
  )),
  ((32, 37), (140, 154), (
    0.8418882744887882, -0.03507867810370698, -0.49110149345201615, 0.05302633362636797,
    0.8071786340902602, -8.124812674529306, -0.0012591868109627184, -0.00012935074502361753
  )),
  ((32, 37), (139, 159), (
    0.8319614257465276, -0.05025270356857862, -0.3294343900612542, 0.04948526425253279,
    0.7532756891774542, -7.582242156026943, -0.0013212711574086327, -0.0003003684248110921
  )),
  ((34, 37), (137, 159), (
    0.8589511422614472, -0.040902435345787885, -0.36812191811256556, 0.06315098535805823,
    0.7750348203034406, -9.363568828999242, -0.0012373471954199079, -0.00023270289362077926
  )),
  ((35, 41), (139, 154), (
    0.8455037777043841, -0.04664848428714724, -0.42566741912061384, 0.04637823184572944,
    0.788429941377457, -7.142247704242852, -0.0012830341056942463, -0.00021217293351479655
  )),
  ((30, 45), (144, 155), (
    0.7914010084871772, -0.05922048362828633, -0.31763713946129124, 0.036579154624469146,
    0.7472598730427091, -6.014658138966106, -0.0013073359085966144, -0.00042300345448779953
  )),
  ((29, 49), (141, 155), (
    0.805563131947475, -0.04932019175188526, -0.4110015979331508, 0.03854700909858402,
    0.7654334663861919, -6.162014740187824, -0.0014102306847203153, -0.00029258497514394707
  )),
  ((27, 53), (140, 153), (
    0.795777032725863, -0.04973606454536984, -0.3481524518169455, 0.0440392668196559,
    0.7651822609915604, -6.930679615743618, -0.0014760612311215343, -0.00041645574828391875
  )),
  ((19, 57), (145, 153), (
    0.7567398340812008, -0.06219779458201795, -0.3213552720090219, 0.03165202597610235,
    0.7543732857637739, -5.312265026322552, -0.0015555168716033648, -0.000384263052672905
  )),
  ((19, 57), (144, 153), (
    0.745234004629022, -0.06125210996951608, -0.31646923484060824, 0.031017553658488434,
    0.7392516955273174, -5.205779422349839, -0.0016366220170216798, -0.0004980343933854424
  )),
  ((19, 55), (141, 154), (
    0.8009441740588495, -0.060345109004438194, -0.31818330202214345, 0.038814778722081306,
    0.7652056376638924, -6.160459880033247, -0.0014904447626626904, -0.0003088081102215613
  )),
  ((16, 57), (143, 156), (
    0.795781248494565, -0.061213942191896256, 3.9459321227175437e-13, 0.06787214891686257,
    0.7861857249536703, -10.288286573314643, -0.0014600251050042926, -0.00025247924905627485
  )),
  ((14, 61), (142, 149), (
    0.838574964045579, -0.06032913410399732, -0.2352836230051742, 0.054139413426402036,
    0.8241221821574586, -8.295361235000929, -0.0012705480664133735, -0.0001805648265203342
  )),
  ((11, 57), (148, 153), (
    0.8558419160909251, -0.07181890204959068, -0.13765289559605678, 0.05204678338322919,
    0.8096166304057538, -8.148213087441013, -0.0009888587415022394, -0.00011207193979494178
  )),
  ((11, 60), (147, 150), (
    0.9135148597515294, -0.09929509345125692, 0.2780262616641333, 0.06328178150382063,
    0.8054044918667757, -9.728135683905414, -0.0005553436559200552, -0.0003799274211367474
  )),
  ((-6, 46), (175, 171), (
    0.7491186827297729, 5.163512846462215e-17, -0.7491186827301305, 0.07072525816330816,
    0.8284958813416292, -12.498163478287443, -0.0007449447366379743, 0.0004549098858523884
  ))
]


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
  command.CommandBuilder("meme_pic.hit_screen", "打穿", "打穿屏幕")
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
    frames: list[Image.Image] = []
    for i in range(6):
      frames.append(Image.open(DIR / f"{i}.png").convert("RGBA"))
    for i, raw in zip(range(6, 22), imutil.sample_frames(target, FRAMETIME)):
      template = Image.open(DIR / f"{i}.png").convert("RGBA")
      pos, size, data = TRANSFORMS[i - 6]
      fg = ImageOps.pad(raw.convert("RGBA"), (140, 120), imutil.scale_resample())
      fg = fg.transform(size, Image.Transform.PERSPECTIVE, data, imutil.resample())
      im = Image.new("RGB", template.size)
      im.paste(fg, pos, fg)
      im.paste(template, mask=template)
      frames.append(im)
    for i in range(22, 29):
      frames.append(Image.open(DIR / f"{i}.png").convert("RGBA"))
    return imutil.to_segment(frames, FRAMETIME, afmt=args.format)

  await matcher.finish(await asyncio.to_thread(make))