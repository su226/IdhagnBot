from pathlib import Path

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image

from util import command, imutil, misc, textutil

DIR = Path(__file__).resolve().parent


whisper = (
  command.CommandBuilder("meme_word.whisper", "低语")
  .category("meme_word")
  .usage("/低语 <文本>")
  .build()
)
@whisper.handle()
async def handle_whisper(args: Message = CommandArg()):
  text = args.extract_plain_text().rstrip()
  if not text:
    await whisper.finish(whisper.__doc__)

  def make() -> MessageSegment:
    template = Image.open(DIR / "template.png")
    text_im = textutil.render(text, "sans", 40, box=template.width * 2 - 20, align="m")
    size = (max(template.width, text_im.width + 20), template.height + text_im.height)
    im = Image.new("RGB", size, (255, 255, 255))
    imutil.paste(im, template, (im.width // 2, 0), anchor="mt")
    imutil.paste(im, text_im, (im.width // 2, template.height), anchor="mt")
    return imutil.to_segment(im)

  await whisper.finish(await misc.to_thread(make))
