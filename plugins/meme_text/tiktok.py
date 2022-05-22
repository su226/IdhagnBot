from io import BytesIO

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image, ImageChops, ImageDraw

from util import command, resources

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
  text = args.extract_plain_text().rstrip() or USAGE
  font = resources.font("sans-bold", 64)
  w, h = font.getsize_multiline(text)
  h += font.getmetrics()[1]
  original = Image.new("L", (w, h))
  draw = ImageDraw.Draw(original)
  draw.multiline_text((0, 0), text, 255, font)
  shifted = Image.new("L", (w, h))
  shifted.paste(original, (-DISPERSION, -DISPERSION))
  subtract = ImageChops.subtract(original, shifted)
  im = Image.new("RGB", (w + PADDING * 2 + DISPERSION, h + PADDING * 2 + DISPERSION), BG)
  draw = ImageDraw.Draw(im)
  draw.bitmap((PADDING, PADDING), original, FG1)
  draw.bitmap((PADDING + DISPERSION, PADDING + DISPERSION), original, FG2)
  draw.bitmap((PADDING + DISPERSION, PADDING + DISPERSION), subtract, FG3)
  f = BytesIO()
  im.save(f, "png")
  await tiktok.finish(MessageSegment.image(f))
