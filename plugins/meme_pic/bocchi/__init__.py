from argparse import Namespace
from pathlib import Path
from typing import List, Tuple

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, imutil, misc
from util.user_aliases import AvatarGetter, DefaultType

DIR = Path(__file__).resolve().parent
TRANSFORMS: List[Tuple[imutil.Size, imutil.Size, imutil.PerspectiveData]] = [
  # RemapTransform((350, 400), ((54, 62), (353, 1), (379, 382), (1, 399)))  # noqa: ERA001
  ((146, 173), (379, 399), (
    1.5135510311733689, 0.2380362155850977, -96.49000104964894, 0.3428681862502599,
    1.6806161916201623, -122.71308593796242, 0.0007098922010365125, 0.0009267649487739304,
  )),
  # RemapTransform((350, 400), ((54, 61), (349, 1), (379, 381), (1, 398)))  # noqa: ERA001
  ((146, 174), (379, 398), (
    1.5344695588304134, 0.24132607305049947, -97.58224663291313, 0.34672637150144936,
    1.704737993215485, -122.71224164722129, 0.0007191678985663559, 0.0009788476059334802,
  )),
  # RemapTransform((350, 400), ((54, 61), (349, 1), (379, 381), (1, 398)))  # noqa: ERA001
  ((152, 174), (379, 398), (
    1.5344695588304134, 0.24132607305049947, -97.58224663291313, 0.34672637150144936,
    1.704737993215485, -122.71224164722129, 0.0007191678985663559, 0.0009788476059334802,
  )),
  # RemapTransform((350, 400), ((54, 61), (335, 1), (379, 381), (1, 398)))  # noqa: ERA001
  ((158, 167), (379, 398), (
    1.6426058279695095, 0.2583326673067143, -104.45900741605679, 0.3863571648713525,
    1.8094393888141642, -131.23908962071573, 0.000815836343972139, 0.0011870465436846901,
  )),
  # RemapTransform((350, 400), ((54, 61), (335, 1), (370, 381), (1, 398)))  # noqa: ERA001
  ((157, 149), (370, 398), (
    1.6302841395265748, 0.2563948349997961, -103.6754284694369, 0.37612016497762224,
    1.7614961059785326, -127.76175137348221, 0.0007875905326561058, 0.0010890375801375018,
  )),
  # RemapTransform((350, 400), ((41, 59), (321, 1), (357, 379), (1, 396)))  # noqa: ERA001
  ((167, 108), (357, 396), (
    1.5703617749436414, 0.18639308901406443, -75.38202502452276, 0.3414026953764736,
    1.648150943196767, -111.23841615904435, 0.000699402402149581, 0.0008932512568269709,
  )),
  # RemapTransform((350, 400), ((41, 57), (315, 1), (357, 377), (1, 394)))  # noqa: ERA001
  ((173, 69), (357, 394), (
    1.6016691015402449, 0.19010909217097152, -76.50465141691033, 0.34434396937832745,
    1.6848258501724935, -110.15317620434386, 0.0007063022143570208, 0.0009754443645130552,
  )),
  # RemapTransform((350, 400), ((41, 56), (309, 1), (353, 380), (1, 393)))  # noqa: ERA001
  ((175, 43), (353, 393), (
    1.6523364130243339, 0.1961230163827572, -78.72868185142104, 0.35001599023483077,
    1.70553246150792, -109.86047344407257, 0.0007552670434594148, 0.0010207486838510877,
  )),
  # RemapTransform((350, 400), ((41, 56), (314, 1), (353, 380), (1, 393)))  # noqa: ERA001
  ((174, 30), (353, 393), (
    1.612300460005681, 0.19137097448133947, -76.82109343119927, 0.33629627216555175,
    1.6692524054762916, -107.26628186545867, 0.0007215771580130765, 0.0009465494840692381,
  )),
  # RemapTransform((350, 400), ((41, 50), (312, 1), (348, 367), (1, 387)))  # noqa: ERA001
  ((171, 18), (348, 387), (
    1.5504252429225398, 0.18402673506502423, -72.76877171308033, 0.2964017174561464,
    1.6392829679717533, -94.1166188142903, 0.0005570565988416992, 0.0009067149151724765,
  )),
  # RemapTransform((350, 400), ((35, 50), (306, 1), (342, 367), (1, 386)))  # noqa: ERA001
  ((178, 14), (342, 386), (
    1.536318531359648, 0.15546080376854757, -61.54418878601936, 0.2889760116853135,
    1.5982142687086387, -90.02487384441623, 0.000545629808486269, 0.0008222574997759615,
  )),
]
TRANSFORM_IDS = [0, 0, 0, 1, 1, 2, 2, 2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10]


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
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
  command.CommandBuilder("meme_pic.bocchi", "波奇手稿")
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
    target = target.resize((350, 400), imutil.scale_resample())
    frames: List[Image.Image] = []
    for i in range(4):
      frames.append(Image.open(DIR / f"{i}.png"))
    for i, transform_id in enumerate(TRANSFORM_IDS):
      pos, size, transform = TRANSFORMS[transform_id]
      template = Image.open(DIR / f"{i + 4}.png").convert("RGBA")
      frame = Image.new("RGB", template.size, (255, 255, 255))
      target1 = target.transform(size, Image.Transform.PERSPECTIVE, transform, imutil.resample())
      frame.paste(target1, pos, target1)
      frame.paste(template, mask=template)
      frames.append(frame)
    return imutil.to_segment(frames, 80, afmt=args.format)

  await matcher.finish(await misc.to_thread(make))
