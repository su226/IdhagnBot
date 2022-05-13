from dataclasses import dataclass
from io import BytesIO
from PIL import Image, ImageDraw
from util import resources
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
import nonebot

Color = tuple[int, int, int]
@dataclass
class Theme:
  margin_outer: int
  margin_text: int
  padding_h: int
  padding_v: int
  radius: int
  bg1: Color
  bg2: Color
  fg1: Color
  fg2: Color

def rounded_rect(draw: ImageDraw.ImageDraw, xywh: tuple[int, int, int, int], radius: int, color: Color):
  im2 = Image.new("L", (radius * 4, radius * 4))
  draw2 = ImageDraw.Draw(im2)
  draw2.ellipse((0, 0, radius * 4 - 1, radius * 4 - 1), 255)
  im2 = im2.resize((radius * 2, radius * 2), Image.ANTIALIAS)
  x, y, w, h = xywh
  draw.bitmap((x, y), im2.crop((0, 0, radius, radius)), color)
  draw.bitmap((x + w - radius, y), im2.crop((radius, 0, radius * 2, radius)), color)
  draw.bitmap((x, y + h - radius), im2.crop((0, radius, radius, radius * 2)), color)
  draw.bitmap((x + w - radius, y + h - radius), im2.crop((radius, radius, radius * 2, radius * 2)), color)
  w -= 1
  h -= 1
  draw.rectangle((x + radius, y, x + w - radius, y + radius), color)
  draw.rectangle((x, y + radius, x + w, y + h - radius), color)
  draw.rectangle((x + radius, y + h - radius, x + w - radius, y + h), color)

def register(names: list[str], brief: str, theme: Theme):
  async def handler(args: Message = CommandArg()):
    text = args.extract_plain_text().split()
    if len(text) == 2:
      left, right = text
    else:
      left = f"用法: /{names[0]}"
      right = f"<左侧文本> <右侧文本>"
    font = resources.font("sans-bold", 64)
    lw, lh = font.getsize(left)
    rw, rh = font.getsize(right)
    h = max(lh, rh) + font.getmetrics()[1]
    im = Image.new("RGB", (lw + rw + theme.margin_text + theme.margin_outer * 2 + theme.padding_h * 2, h + theme.padding_v * 2 + theme.margin_outer * 2), theme.bg1)
    draw = ImageDraw.Draw(im)
    rounded_rect(draw, (lw + theme.margin_outer + theme.margin_text, theme.margin_outer, rw + theme.padding_h * 2, h + theme.padding_v * 2), theme.radius, theme.bg2)
    text_y = theme.margin_outer + theme.padding_v
    draw.text((theme.margin_outer, text_y), left, theme.fg1, font)
    draw.text((theme.margin_outer + lw + theme.margin_text + theme.padding_h, text_y), right, theme.fg2, font)
    f = BytesIO()
    im.save(f, "png")
    await matcher.finish(MessageSegment.image(f))
  matcher = nonebot.on_command(names[0], aliases=set(names[1:]), handlers=[handler])
  matcher.__cmd__ = names
  matcher.__brief__ = brief
  matcher.__doc__ = f"/{names[0]} <左侧文本> <右侧文本>"

register(["p站", "ph"], "生成你懂得的logo", Theme(32, 8, 8, 8, 8, (0, 0, 0), (255, 153, 0), (255, 255, 255), (0, 0, 0)))
register(["油管", "yt", "youtube"], "生成油管logo", Theme(32, 6, 9, 9, 21, (255, 255, 255), (205, 32, 31), (0, 0, 0), (255, 255, 255)))
