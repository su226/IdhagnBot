from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image, ImageChops

from util import command, imutil, misc, textutil

BG = (28, 11, 27)
FG1 = (0, 242, 234)
FG2 = (255, 255, 255)
FG3 = (255, 0, 79)
PADDING = 32
DISPERSION = 3

tiktok = (
  command.CommandBuilder("meme_word.tiktok", "抖音", "tiktok")
  .category("meme_word")
  .brief("记录每种生物")
  .usage("/抖音 <文本>")
  .build()
)
@tiktok.handle()
async def handle_tiktok(args: Message = CommandArg()):
  def make() -> MessageSegment:
    content = args.extract_plain_text().rstrip() or tiktok.__doc__ or ""
    center = textutil.render(content, "sans bold", 64, color=FG2)
    w, h = center.size
    topleft = Image.new("L", (w, h))
    topleft.paste(center, mask=center)
    shifted = Image.new("L", (w, h))
    shifted.paste(topleft, (-DISPERSION, -DISPERSION))
    bottomright = ImageChops.subtract(topleft, shifted)
    im = Image.new("RGB", (w + PADDING * 2 + DISPERSION, h + PADDING * 2 + DISPERSION), BG)
    im.paste(FG1, (PADDING, PADDING), topleft)
    im.paste(center, (PADDING + DISPERSION, PADDING + DISPERSION), center)
    im.paste(FG3, (PADDING + DISPERSION, PADDING + DISPERSION), bottomright)
    return imutil.to_segment(im)
  await tiktok.finish(await misc.to_thread(make))
