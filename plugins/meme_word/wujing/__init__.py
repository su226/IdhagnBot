from pathlib import Path

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image

from util import command, imutil, misc, textutil

DIR = Path(__file__).resolve().parent


wujing = (
  command.CommandBuilder("meme_word.wujing", "吴京")
  .category("meme_word")
  .usage("/吴京 <文本>\n必须包含“中国”两字")
  .build()
)
@wujing.handle()
async def handle_wujing(args: Message = CommandArg()):
  text = args.extract_plain_text()
  try:
    i = text.index("中国")
  except ValueError:
    await wujing.finish(wujing.__doc__)

  def make() -> MessageSegment:
    left = text[:i].rsplit(None, 1)
    right = text[i + 2:].split(None, 1)
    im = Image.open(DIR / "template.jpg")
    if len(left) == 2:
      left1_im = textutil.render(left[-2], "sans", 85, color=(255, 255, 255), align="l")
      left1_im = imutil.contain_down(left1_im, 837, 130)
      imutil.paste(im, left1_im, (50, 485), anchor="lm")
    if left:
      left2_im = textutil.render(left[-1], "sans", 85, color=(255, 255, 255), align="r")
      left2_im = imutil.contain_down(left2_im, 330, 130)
      imutil.paste(im, left2_im, (350, 625), anchor="rm")
    if right:
      right1_im = textutil.render(right[0], "sans", 85, color=(255, 255, 255), align="l")
      right1_im = imutil.contain_down(right1_im, 307, 130)
      imutil.paste(im, right1_im, (610, 605), anchor="lm")
    if len(right) == 2:
      right2_im = textutil.render(right[1], "sans", 85, color=(255, 255, 255), align="r")
      right2_im = imutil.contain_down(right2_im, 837, 130)
      imutil.paste(im, right2_im, (887, 745), anchor="rm")
    return imutil.to_segment(im)

  await wujing.finish(await misc.to_thread(make))
