import shlex
from pathlib import Path

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image

from util import command, imutil, misc, textutil

DIR = Path(__file__).resolve().parent


higheq = (
  command.CommandBuilder("meme_word.higheq", "高情商")
  .category("meme_word")
  .usage("/高情商 <低情商文本> <高情商文本>")
  .build()
)
@higheq.handle()
async def handle_higheq(args: Message = CommandArg()):
  try:
    argv = shlex.split(args.extract_plain_text())
  except ValueError as e:
    await higheq.finish(str(e))
  if len(argv) != 2:
    await higheq.finish(higheq.__doc__)

  def make() -> MessageSegment:
    left, right = argv
    left_im = textutil.render(
      left, "sans", 100,
      color=(255, 255, 255), stroke=5, stroke_color=(0, 0, 0), box=843, align="m"
    )
    left_im = imutil.contain_down(left_im, 562, 600)
    right_im = textutil.render(
      right, "sans", 100,
      color=(255, 255, 255), stroke=5, stroke_color=(0, 0, 0), box=843, align="m"
    )
    right_im = imutil.contain_down(right_im, 562, 600)
    im = Image.open(DIR / "template.jpg")
    imutil.paste(im, left_im, (321, 840), anchor="mm")
    imutil.paste(im, right_im, (963, 840), anchor="mm")
    return imutil.to_segment(im)

  await higheq.finish(await misc.to_thread(make))
