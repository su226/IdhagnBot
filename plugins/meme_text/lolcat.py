import html
import math
import random
from io import BytesIO

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image

from util import command, text

SIZE = 32
PADDING = SIZE
OMEGA = 0.00005 / SIZE


def rainbow(x: float, phi: float) -> str:
  r = math.sin(OMEGA * x + phi) * 127 + 128
  g = math.sin(OMEGA * x + phi + math.pi * 2 / 3) * 127 + 128
  b = math.sin(OMEGA * x + phi + math.pi * 4 / 3) * 127 + 128
  return f"#{int(r):02x}{int(g):02x}{int(b):02x}"


USAGE = '''\
/lolcat <文本>
灵感来自github.com/busyloop/lolcat'''
lolcat = (
  command.CommandBuilder("meme_text.lolcat", "lolcat")
  .brief("彩虹和独角兽！")
  .usage(USAGE)
  .build())


@lolcat.handle()
async def handle_lolcat(arg: Message = CommandArg()):
  content = arg.extract_plain_text().strip() or USAGE
  layout = text.layout(content, "sans", SIZE)
  pieces = []
  phi = random.uniform(0, 2 * math.pi)
  it = layout.get_iter()
  for ch in content:
    rect = it.get_char_extents()
    color = rainbow(rect.x + rect.y, phi)
    pieces.append(f"<span color='{color}'>{html.escape(ch)}</span>")
    it.next_char()
  layout.set_markup("".join(pieces))
  _, rect = layout.get_pixel_extents()
  im = Image.new("RGB", (rect.width + PADDING * 2, rect.height + PADDING * 2), (33, 33, 33))
  text.paste(im, (PADDING, PADDING), layout)
  f = BytesIO()
  im.save(f, "PNG")
  await lolcat.finish(MessageSegment.image(f))
