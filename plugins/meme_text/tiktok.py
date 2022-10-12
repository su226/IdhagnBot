from io import BytesIO

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image, ImageChops, ImageDraw

from util import command, text

BG = (28, 11, 27)
FG1 = (0, 242, 234)
FG2 = (255, 255, 255)
FG3 = (255, 0, 79)
PADDING = 32
DISPERSION = 3

USAGE = "/抖音 <文本>"
tiktok = (
  command.CommandBuilder("meme_text.tiktok", "抖音", "tiktok")
  .brief("记录每种生物")
  .build())


@tiktok.handle()
async def handle_tiktok(args: Message = CommandArg()):
  content = args.extract_plain_text().rstrip() or USAGE
  center = text.render(content, "sans bold", 64, color=FG2)
  w, h = center.size
  topleft = Image.new("L", (w, h))
  topleft.paste(center, mask=center)
  shifted = Image.new("L", (w, h))
  shifted.paste(topleft, (-DISPERSION, -DISPERSION))
  bottomright = ImageChops.subtract(topleft, shifted)
  im = Image.new("RGB", (w + PADDING * 2 + DISPERSION, h + PADDING * 2 + DISPERSION), BG)
  draw = ImageDraw.Draw(im)
  draw.bitmap((PADDING, PADDING), topleft, FG1)
  im.paste(center, (PADDING + DISPERSION, PADDING + DISPERSION), center)
  draw.bitmap((PADDING + DISPERSION, PADDING + DISPERSION), bottomright, FG3)
  f = BytesIO()
  im.save(f, "png")
  await tiktok.finish(MessageSegment.image(f))
