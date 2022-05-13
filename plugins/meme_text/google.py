from io import BytesIO
from PIL import Image, ImageDraw
from util import resources
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
import random
import nonebot

COLORS = [(66, 133, 244), (234, 67, 53), (251, 188, 5), (52, 168, 83)]
PADDING = 32

google = nonebot.on_command("谷歌", aliases={"google"})
google.__cmd__ = ["谷歌", "google"]
google.__brief__ = "G,O,O,G,L,E,咕噜咕噜"
google.__doc__ = "/谷歌 <文本>"
@google.handle()
async def handle_google(args: Message = CommandArg()):
  text = args.extract_plain_text().rstrip() or google.__doc__
  font = resources.font("sans-bold", 64)
  line_height = font.getsize("A")[1] + 4
  w, h = font.getsize_multiline(text)
  h += font.getmetrics()[1]
  im = Image.new("RGB", (w + PADDING * 2, h + PADDING * 2), (255, 255, 255))
  draw = ImageDraw.Draw(im)
  x = 0
  y = 0
  colors = COLORS.copy()
  random.shuffle(colors)
  for ch in text:
    if ch == "\n":
      x = 0
      y += line_height
      continue
    # 防止两个相同的颜色挨在一起
    i = random.randrange(len(colors) - 1)
    draw.text((PADDING + x, PADDING + y), ch, colors[i], font)
    colors[i], colors[-1] = colors[-1], colors[i]
    x += font.getsize(ch)[0]
  f = BytesIO()
  im.save(f, "png")
  await google.finish(MessageSegment.image(f))
