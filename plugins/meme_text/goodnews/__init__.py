import asyncio
from pathlib import Path

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image

from util import command, imutil, textutil

DIR = Path(__file__).resolve().parent


goodnews = (
  command.CommandBuilder("meme_text.goodnews", "喜报")
  .category("meme_word")
  .brief("NullPointerException")
  .usage("/喜报 <文本>")
  .build()
)
@goodnews.handle()
async def handle_goodnews(args: Message = CommandArg()):
  def make() -> MessageSegment:
    content = args.extract_plain_text().rstrip() or goodnews.__doc__ or ""
    im = Image.open(DIR / "template.jpg")
    text_im = textutil.render(
      content, "sans", 80, color=(238, 0, 0), stroke=6, stroke_color=(255, 255, 153), align="m"
    )
    text_im = imutil.contain_down(text_im, 480, 250)
    imutil.paste(im, text_im, (im.width // 2, im.height // 2), anchor="mm")
    return imutil.to_segment(im)
  await goodnews.finish(await asyncio.to_thread(make))
