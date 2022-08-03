import html
import random
from io import BytesIO

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image

from util import command, text

COLORS = ["4285f4", "ea4335", "fbbc05", "34a853"]
PADDING = 32

USAGE = "/谷歌 <文本>"
google = (
  command.CommandBuilder("meme_text.google", "谷歌", "google")
  .brief("G,O,O,G,L,E,咕噜咕噜")
  .build())


@google.handle()
async def handle_google(args: Message = CommandArg()):
  content = args.extract_plain_text().rstrip() or USAGE
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
  text_im = text.render("".join(pieces), "sans", 64, markup=True)
  p = PADDING * 2
  im = Image.new("RGB", (text_im.width + p, text_im.height + p), (255, 255, 255))
  im.paste(text_im, (PADDING, PADDING), text_im)
  f = BytesIO()
  im.save(f, "png")
  await google.finish(MessageSegment.image(f))
