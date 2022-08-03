from dataclasses import dataclass
from io import BytesIO

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image, ImageDraw

from util import command, text, util

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


def rounded_rect(
  draw: ImageDraw.ImageDraw, xywh: tuple[int, int, int, int], radius: int, color: Color
):
  im2 = Image.new("L", (radius * 4, radius * 4))
  draw2 = ImageDraw.Draw(im2)
  draw2.ellipse((0, 0, radius * 4 - 1, radius * 4 - 1), 255)
  im2 = im2.resize((radius * 2, radius * 2), util.scale_resample)
  x, y, w, h = xywh
  draw.bitmap((x, y), im2.crop((0, 0, radius, radius)), color)
  draw.bitmap((x + w - radius, y), im2.crop((radius, 0, radius * 2, radius)), color)
  draw.bitmap((x, y + h - radius), im2.crop((0, radius, radius, radius * 2)), color)
  draw.bitmap(
    (x + w - radius, y + h - radius), im2.crop((radius, radius, radius * 2, radius * 2)), color)
  w -= 1
  h -= 1
  draw.rectangle((x + radius, y, x + w - radius, y + radius), color)
  draw.rectangle((x, y + radius, x + w, y + h - radius), color)
  draw.rectangle((x + radius, y + h - radius, x + w - radius, y + h), color)


def register(node: str, names: list[str], brief: str, theme: Theme):
  async def handler(args: Message = CommandArg()):
    content = args.extract_plain_text().split()
    if len(content) == 2:
      left, right = content
    else:
      left = f"用法: /{names[0]}"
      right = "<左侧文本> <右侧文本>"
    left_im = text.render(left, "sans bold", 64, color=theme.fg1)
    right_im = text.render(right, "sans bold", 64, color=theme.fg2)
    lw, lh = left_im.size
    rw, rh = right_im.size
    h = max(lh, rh)
    im = Image.new("RGB", (
      lw + rw + theme.margin_text + theme.margin_outer * 2 + theme.padding_h * 2,
      h + theme.padding_v * 2 + theme.margin_outer * 2
    ), theme.bg1)
    draw = ImageDraw.Draw(im)
    rounded_rect(draw, (
      lw + theme.margin_outer + theme.margin_text, theme.margin_outer,
      rw + theme.padding_h * 2, h + theme.padding_v * 2
    ), theme.radius, theme.bg2)
    text_y = theme.margin_outer + theme.padding_v
    im.paste(
      left_im, (theme.margin_outer, text_y), left_im)
    im.paste(
      right_im, (theme.margin_outer + lw + theme.margin_text + theme.padding_h, text_y), right_im)
    f = BytesIO()
    im.save(f, "png")
    await matcher.finish(MessageSegment.image(f))
  matcher = (
    command.CommandBuilder(node, *names)
    .brief(brief)
    .usage(f"/{names[0]} <左侧文本> <右侧文本>")
    .build())
  matcher.handle()(handler)


register("meme_text.pornhub", ["p站", "ph"], "生成你懂得的logo", Theme(
  32, 8, 8, 8, 8, (0, 0, 0), (255, 153, 0), (255, 255, 255), (0, 0, 0)))
register("meme_text.youtube", ["油管", "yt", "youtube"], "生成油管logo", Theme(
  32, 6, 9, 9, 21, (255, 255, 255), (205, 32, 31), (0, 0, 0), (255, 255, 255)))
