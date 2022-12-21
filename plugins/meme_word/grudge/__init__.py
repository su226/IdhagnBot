from datetime import date
from pathlib import Path

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image

from util import command, imutil, misc, textutil

DIR = Path(__file__).resolve().parent


grudge = (
  command.CommandBuilder("meme_word.grudge", "记仇")
  .category("meme_word")
  .usage("/记仇 <文本>")
  .build()
)
@grudge.handle()
async def handle_grudge(args: Message = CommandArg()):
  text = args.extract_plain_text().rstrip()
  if not text:
    await grudge.finish(grudge.__doc__)

  def make() -> MessageSegment:
    nonlocal text
    text = f"{date.today():%Y年%m月%d日} 晴\n{text}\n这个仇我先记下了"
    template = Image.open(DIR / "template.png")
    text_im = textutil.render(text, "sans", 45, box=template.width * 2 - 20, align="m")
    size = (max(text_im.width + 20, template.width), text_im.height + template.height)
    im = Image.new("RGB", size, (255, 255, 255))
    imutil.paste(im, template, (im.width // 2, 0), anchor="mt")
    imutil.paste(im, text_im, (im.width // 2, template.height), anchor="mt")
    return imutil.to_segment(im)

  await grudge.finish(await misc.to_thread(make))
