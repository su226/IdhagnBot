import shlex
from pathlib import Path

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image

from util import command, imutil, misc, textutil

DIR = Path(__file__).resolve().parent


chips = (
  command.CommandBuilder("meme_word.chips", "整点薯条", "薯条")
  .category("meme_word")
  .usage("/整点薯条 <文本1> <文本2> <文本3> <文本4>")
  .build()
)
@chips.handle()
async def handle_not_call_me(args: Message = CommandArg()):
  try:
    argv = shlex.split(args.extract_plain_text())
  except ValueError as e:
    await chips.finish(str(e))
  if len(argv) != 4:
    await chips.finish(chips.__doc__)

  def make() -> MessageSegment:
    text1, text2, text3, text4 = argv
    text1_im = textutil.render(text1, "sans", 40, box=187, align="m")
    text1_im = imutil.contain_down(text1_im, 125, 76)
    text2_im = textutil.render(text2, "sans", 40, box=145, align="m")
    text2_im = imutil.contain_down(text2_im, 97, 98)
    text3_im = textutil.render(text3, "sans", 40, box=390, align="m")
    text3_im = imutil.contain_down(text3_im, 260, 63)
    text4_im = textutil.render(text4, "sans", 40, box=300, align="m")
    text4_im = imutil.contain_down(text4_im, 200, 70)
    im = Image.open(DIR / "template.jpg")
    imutil.paste(im, text1_im, (460, 92), anchor="mm")
    imutil.paste(im, text2_im, (618, 111), anchor="mm")
    imutil.paste(im, text3_im, (195, 431), anchor="mm")
    imutil.paste(im, text4_im, (530, 435), anchor="mm")
    return imutil.to_segment(im)

  await chips.finish(await misc.to_thread(make))
