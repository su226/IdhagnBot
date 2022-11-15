import asyncio
from pathlib import Path
import math

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image, ImageOps

from util import command, imutil, textutil

DIR = Path(__file__).resolve().parent


osu = (
  command.CommandBuilder("meme_text.osu", "osu")
  .category("meme_word")
  .brief("Click the circles?")
  .usage("/osu <文本>\n默认为“osu?”")
  .build()
)
@osu.handle()
async def handle_osu(args: Message = CommandArg()):
  def make() -> MessageSegment:
    content = args.extract_plain_text().rstrip() or "osu?"
    font = textutil.special_font("osu", "sans bold")
    text_im = textutil.render(content, font, 100, color=(255, 255, 255))
    ratio = min(270 / math.hypot(text_im.width, text_im.height), 1)
    text_im = ImageOps.scale(text_im, ratio, imutil.scale_resample())
    im = Image.open(DIR / "template.png")
    im.alpha_composite(text_im, (175 - text_im.width // 2, 175 - text_im.height // 2))
    return imutil.to_segment(im)
  await osu.finish(await asyncio.to_thread(make))
