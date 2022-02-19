from io import BytesIO
import random
from PIL import Image, ImageDraw, ImageFont, ImageChops
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
import nonebot

FONT = ImageFont.truetype("/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc", 64)
COLORS = [(66, 133, 244), (234, 67, 53), (251, 188, 5), (52, 168, 83)]
PADDING = 32
LINE_HEIGHT = FONT.getsize("A")[1] + 4

tiktok = nonebot.on_command("谷歌", aliases={"google"})
tiktok.__cmd__ = ["谷歌", "google"]
tiktok.__brief__ = "G,O,O,G,L,E,咕噜咕噜"
tiktok.__doc__ = "/谷歌 <文本>"
@tiktok.handle()
async def handle_tiktok(args: Message = CommandArg()):
  text = args.extract_plain_text().rstrip()
  w, h = FONT.getsize_multiline(text)
  h += FONT.getmetrics()[1]
  im = Image.new("RGB", (w + PADDING * 2, h + PADDING * 2), (255, 255, 255))
  draw = ImageDraw.Draw(im)
  x = 0
  y = 0
  colors = COLORS.copy()
  random.shuffle(colors)
  for ch in text:
    if ch == "\n":
      x = 0
      y += LINE_HEIGHT
      continue
    # 防止两个相同的颜色挨在一起
    i = random.randrange(len(colors) - 1)
    draw.text((PADDING + x, PADDING + y), ch, colors[i], FONT)
    colors[i], colors[-1] = colors[-1], colors[i]
    x += FONT.getsize(ch)[0]
  f = BytesIO()
  im.save(f, "png")
  await tiktok.finish(MessageSegment.image(f))
