from dataclasses import dataclass
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
import nonebot

FONT = ImageFont.truetype("/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc", 64)

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

def register(names: list[str], brief: str, theme: Theme):
  async def handler(args: Message = CommandArg()):
    text = args.extract_plain_text().split()
    if len(text) != 2:
      await matcher.finish("请刚好输入两段空格分割的文字")
    left, right = text
    w, h = FONT.getsize(left)
    w2, h2 = FONT.getsize(right)
    h = max(h, h2)
    im = Image.new("RGB", (w + w2 + theme.margin_text + theme.margin_outer * 2 + theme.padding_h * 2, h + theme.padding_v * 2 + theme.margin_outer * 2), theme.bg1)
    draw = ImageDraw.Draw(im)
    box_x = w + theme.margin_outer + theme.margin_text
    box_y = theme.margin_outer
    draw.rounded_rectangle((box_x, box_y, box_x + w2 + theme.padding_h * 2, box_y + h + theme.padding_v * 2), theme.radius, theme.bg2)
    text_y = theme.margin_outer + theme.padding_v - FONT.getmetrics()[1] / 2
    draw.text((theme.margin_outer, text_y), left, theme.fg1, FONT)
    draw.text((theme.margin_outer + w + theme.margin_text + theme.padding_h, text_y), right, theme.fg2, FONT)
    f = BytesIO()
    im.save(f, "png")
    await matcher.finish(MessageSegment.image(f))
  matcher = nonebot.on_command(names[0], aliases=set(names[1:]), handlers=[handler])
  matcher.__cmd__ = names
  matcher.__brief__ = brief
  matcher.__doc__ = "/{} <左侧文本> <右侧文本>".format(names[0])

register(["p站", "ph"], "生成你懂得的logo", Theme(32, 16, 16, 12, 24, (0, 0, 0), (255, 153, 0), (255, 255, 255), (0, 0, 0)))
register(["油管", "yt", "youtube"], "生成油管logo", Theme(32, 16, 16, 12, 32, (238, 28, 27), (255, 255, 255), (255, 255, 255), (238, 28, 27)))
