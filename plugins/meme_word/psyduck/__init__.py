import shlex
from pathlib import Path
from typing import List, Optional, Tuple

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image

from util import command, imutil, misc, textutil

DIR = Path(__file__).resolve().parent
TRANSFORMS: List[Optional[Tuple[bool, imutil.Size, imutil.Size, imutil.PerspectiveData]]] = [
  # RemapTransform((155, 100), ((0, 11), (154, 0), (161, 89), (20, 104))), (18, 42)  # noqa: ERA001
  (False, (18, 42), (161, 104), (
    0.9271210740019624, -0.19938087612945843, 2.193189637424667, 0.06884884513359757,
    0.9638838318703977, -10.602722150574163, -0.00042019962154471165, -0.0007828295663741694,
  )),
  # RemapTransform((155, 100), ((0, 9), (153, 0), (159, 89), (20, 101))), (15, 38)  # noqa: ERA001
  (False, (15, 38), (159, 101), (
    0.947679647643337, -0.20601731470506662, 1.8541558323462077, 0.056998313321107885,
    0.9689713264588444, -8.720741938129555, -0.0003437005303910817, -0.0008937891721368285,
  )),
  # RemapTransform((155, 100), ((0, 7), (148, 0), (156, 89), (21, 97))), (14, 23)  # noqa: ERA001
  (False, (14, 23), (156, 97), (
    1.0092369649899, -0.23548862516430902, 1.6484203761503307, 0.04715882706890523,
    0.9970723437426361, -6.979506406197771, -0.00017369262447010668, -0.0009183916683843229,
  )),
  None,
  # RemapTransform((155, 100), ((10, 0), (143, 17), (124, 104), (0, 84))), (298, 18)  # noqa: ERA001, E501
  (True, (298, 18), (143, 104), (
    1.2134183587937442, 0.1444545665230681, -12.134183587938582, -0.1414104402303685,
    1.1063287382728835, 1.4141044023038816, 0.0004788659432742291, -0.0006731287598540469,
  )),
  # RemapTransform((155, 100), ((13, 0), (143, 27), (125, 113), (0, 83))), (298, 30)  # noqa: ERA001, E501
  (True, (298, 30), (143, 113), (
    1.2180496357484907, 0.19077885861120172, -15.834645264728085, -0.23589081013623264,
    1.1357705673225826, 3.0665805317714274, 0.0004439859555503819, -0.00032101956391023,
  )),
  # RemapTransform((155, 100), ((13, 0), (143, 27), (125, 113), (0, 83))), (298, 26)  # noqa: ERA001, E501
  (True, (298, 26), (143, 113), (
    1.2180496357484907, 0.19077885861120172, -15.834645264728085, -0.23589081013623264,
    1.1357705673225826, 3.0665805317714274, 0.0004439859555503819, -0.00032101956391023,
  )),
  # RemapTransform((155, 100), ((13, 0), (143, 27), (125, 113), (0, 83))), (298, 30)  # noqa: ERA001, E501
  (True, (298, 30), (143, 113), (
    1.2180496357484907, 0.19077885861120172, -15.834645264728085, -0.23589081013623264,
    1.1357705673225826, 3.0665805317714274, 0.0004439859555503819, -0.00032101956391023,
  )),
  # RemapTransform((155, 100), ((13, 0), (143, 27), (125, 113), (0, 83))), (302, 20)  # noqa: ERA001, E501
  (True, (302, 20), (143, 113), (
    1.2180496357484907, 0.19077885861120172, -15.834645264728085, -0.23589081013623264,
    1.1357705673225826, 3.0665805317714274, 0.0004439859555503819, -0.00032101956391023,
  )),
  # RemapTransform((155, 100), ((13, 0), (141, 23), (120, 102), (0, 82))), (300, 24)  # noqa: ERA001, E501
  (True, (300, 24), (141, 102), (
    1.1539223010807784, 0.18293890139085145, -15.00098991405039, -0.19905782981154943,
    1.107800096342553, 2.5877517875499225, -1.0654553959991292e-05, -0.0008015415015074267,
  )),
  # RemapTransform((155, 100), ((13, 0), (140, 22), (118, 100), (0, 82))), (299, 22)  # noqa: ERA001, E501
  (True, (299, 22), (140, 100), (
    1.149446531715971, 0.1822293281988812, -14.942804912307574, -0.18976845045183158,
    1.0954815094264514, 2.466989855874295, -8.330440675658217e-05, -0.0009394544355069482,
  )),
  # RemapTransform((155, 100), ((9, 0), (128, 16), (109, 89), (0, 80))), (303, 23)  # noqa: ERA001
  (True, (303, 23), (128, 89), (
    1.1799599814867217, 0.1327454979172559, -10.619639833380635, -0.14903545548508768,
    1.1084512001703222, 1.3413190993658817, -0.00047208835289474995, -0.0012478231108760808,
  )),
  None,
  # RemapTransform((155, 100), ((0, 13), (152, 0), (158, 89), (17, 109))), (35, 36)  # noqa: ERA001
  (False, (35, 36), (158, 109), (
    0.9099663448711841, -0.1611398735709377, 2.0948183564223495, 0.08107735568640635,
    0.9479813895641307, -12.323758064333685, -0.00061928256465016, -0.0006020817610338605,
  )),
  # RemapTransform((155, 100), ((0, 13), (152, 0), (158, 89), (17, 109))), (31, 29)  # noqa: ERA001
  (False, (31, 29), (158, 109), (
    0.9099663448711841, -0.1611398735709377, 2.0948183564223495, 0.08107735568640635,
    0.9479813895641307, -12.323758064333685, -0.00061928256465016, -0.0006020817610338605,
  )),
  # RemapTransform((155, 100), ((0, 17), (149, 0), (155, 90), (17, 120))), (45, 33)  # noqa: ERA001
  (False, (45, 33), (155, 120), (
    0.8665867807566694, -0.14302888614429285, 2.431491064452817, 0.10055374050252758,
    0.8813239608750914, -14.982507334876743, -0.0010152447976966104, -0.00048235852376988034,
  )),
  # RemapTransform((155, 100), ((0, 14), (152, 0), (156, 91), (17, 115))), (40, 27)  # noqa: ERA001
  (False, (40, 27), (156, 115), (
    0.8775878065957703, -0.1477127991299661, 2.067979187818257, 0.08164009644636602,
    0.8863781899891012, -12.40929465984752, -0.0008293155437022301, -0.000667659543236423,
  )),
  # RemapTransform((155, 100), ((0, 12), (154, 0), (158, 90), (17, 109))), (35, 28)  # noqa: ERA001
  (False, (35, 28), (158, 109), (
    0.8974854364633884, -0.15729126206058325, 1.8874951447261266, 0.07210553064125778,
    0.9253543098961445, -11.104251718754098, -0.000624203922912113, -0.0007296964449745016,
  )),
]

psyduck = (
  command.CommandBuilder("meme_word.psyduck", "可达鸭")
  .category("meme_word")
  .usage("/可达鸭 <左侧文本> <右侧文本>")
  .build()
)
@psyduck.handle()
async def handle_psyduck(args: Message = CommandArg()):
  try:
    argv = shlex.split(args.extract_plain_text())
  except ValueError as e:
    await psyduck.finish(str(e))
  if len(argv) != 2:
    await psyduck.finish(psyduck.__doc__)

  def make() -> MessageSegment:
    left, right = argv
    left_im = textutil.render(left, "sans", 60, box=233, align="m")
    left_im = imutil.center_pad(left_im, 155, 100)
    right_im = textutil.render(right, "sans", 60, box=233, align="m")
    right_im = imutil.center_pad(right_im, 155, 100)
    frames: List[Image.Image] = []
    for i, data in enumerate(TRANSFORMS):
      frame = Image.open(DIR / f"{i}.jpg")
      if data is not None:
        is_right, pos, size, transform = data
        text_im = (right_im if is_right else left_im).transform(
          size, Image.Transform.PERSPECTIVE, transform, imutil.resample(),
        )
        frame.paste(text_im, pos, text_im)
      frames.append(frame)
    return imutil.to_segment(frames, 200)

  await psyduck.finish(await misc.to_thread(make))
