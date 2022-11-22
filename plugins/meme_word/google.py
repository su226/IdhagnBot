import asyncio
import html
import random

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image

from util import command, imutil, textutil

COLORS = ["4285f4", "ea4335", "fbbc05", "34a853"]
PADDING = 32

google = (
  command.CommandBuilder("meme_word.google", "谷歌", "google")
  .category("meme_word")
  .brief("G,O,O,G,L,E,咕噜咕噜")
  .usage("/谷歌 <文本>")
  .build()
)
@google.handle()
async def handle_google(args: Message = CommandArg()):
  def make() -> MessageSegment:
    content = args.extract_plain_text().rstrip() or google.__doc__ or ""
    colors = COLORS.copy()
    random.shuffle(colors)
    pieces = []
    for ch in content:
      if ch == "\n":
        pieces.append(ch)
        continue
      # 防止两个相同的颜色挨在一起
      i = random.randrange(len(colors) - 1)
      pieces.append(f"<span color='#{colors[i]}'>{html.escape(ch)}</span>")
      colors[i], colors[-1] = colors[-1], colors[i]
    text_im = textutil.render("".join(pieces), "sans", 64, markup=True)
    p = PADDING * 2
    im = Image.new("RGB", (text_im.width + p, text_im.height + p), (255, 255, 255))
    im.paste(text_im, (PADDING, PADDING), text_im)
    return imutil.to_segment(im)
  await google.finish(await asyncio.to_thread(make))
