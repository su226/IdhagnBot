from dataclasses import dataclass
from typing import List, Tuple

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image, ImageDraw

from util import command, imutil, misc, textutil

Color = Tuple[int, int, int]


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


def register(node: str, names: List[str], brief: str, theme: Theme):
  async def handler(args: Message = CommandArg()):
    def make() -> MessageSegment:
      content = args.extract_plain_text().split()
      if len(content) == 2:
        left, right = content
      else:
        left = f"用法: /{names[0]}"
        right = "<左侧文本> <右侧文本>"
      left_im = textutil.render(left, "sans bold", 64, color=theme.fg1)
      right_im = textutil.render(right, "sans bold", 64, color=theme.fg2)
      lw, lh = left_im.size
      rw, rh = right_im.size
      h = max(lh, rh)
      im = Image.new("RGB", (
        lw + rw + theme.margin_text + theme.margin_outer * 2 + theme.padding_h * 2,
        h + theme.padding_v * 2 + theme.margin_outer * 2
      ), theme.bg1)
      rounded_w = rw + theme.padding_h * 2
      rounded_h = h + theme.padding_v * 2
      rounded_im = Image.new("L", (rounded_w * 2, rounded_h * 2))
      ImageDraw.Draw(rounded_im).rounded_rectangle(
        (0, 0, rounded_w * 2 - 1, rounded_h * 2 - 1), theme.radius, 255
      )
      rounded_im = rounded_im.resize((rounded_w, rounded_h), imutil.scale_resample())
      im.paste(
        theme.bg2, (lw + theme.margin_outer + theme.margin_text, theme.margin_outer), rounded_im
      )
      text_y = theme.margin_outer + theme.padding_v
      im.paste(left_im, (theme.margin_outer, text_y), left_im)
      im.paste(
        right_im, (theme.margin_outer + lw + theme.margin_text + theme.padding_h, text_y), right_im
      )
      return imutil.to_segment(im)
    await matcher.finish(await misc.to_thread(make))
  matcher = (
    command.CommandBuilder(node, *names)
    .category("meme_word")
    .brief(brief)
    .usage(f"/{names[0]} <左侧文本> <右侧文本>")
    .build()
  )
  matcher.handle()(handler)


register("meme_word.pornhub", ["p站", "ph"], "生成你懂得的logo", Theme(
  32, 8, 8, 8, 8, (0, 0, 0), (255, 153, 0), (255, 255, 255), (0, 0, 0)
))
register("meme_word.youtube", ["油管", "yt", "youtube"], "生成油管logo", Theme(
  32, 6, 9, 9, 21, (255, 255, 255), (205, 32, 31), (0, 0, 0), (255, 255, 255)
))
