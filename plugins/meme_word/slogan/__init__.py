import shlex
from pathlib import Path

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image

from util import command, imutil, misc, textutil

DIR = Path(__file__).resolve().parent


slogan = (
  command.CommandBuilder("meme_word.slogan", "口号")
  .category("meme_word")
  .usage("/口号 <左1> <右1> [<左2> <右2>...]\n必须是偶数条")
  .build()
)
@slogan.handle()
async def handle_slogan(args: Message = CommandArg()):
  try:
    argv = shlex.split(args.extract_plain_text())
  except ValueError as e:
    await slogan.finish(str(e))
  if not argv or len(argv) % 2 != 0:
    await slogan.finish(slogan.__doc__)

  def make() -> MessageSegment:
    template = Image.open(DIR / "template.png")
    count = len(argv) // 2
    im = Image.new("RGB", (template.width, template.height * count + (count - 1) * 2))
    for i, (left, right) in enumerate(misc.chunked(argv, 2)):
      y = i * (template.height + 2)
      im.paste(template, (0, y))
      y += 28
      left_im = textutil.render(left, "sans", 40, box=426, align="m")
      left_im = imutil.contain_down(left_im, 284, 56)
      imutil.paste(im, left_im, (152, y), anchor="mm")
      right_im = textutil.render(right, "sans", 40, box=426, align="m")
      right_im = imutil.contain_down(right_im, 284, 56)
      imutil.paste(im, right_im, (458, y), anchor="mm")
    return imutil.to_segment(im)

  await slogan.finish(await misc.to_thread(make))
