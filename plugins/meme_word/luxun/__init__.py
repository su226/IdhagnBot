import asyncio
from pathlib import Path

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image

from util import command, imutil, textutil

DIR = Path(__file__).resolve().parent


luxun = (
  command.CommandBuilder("meme_word.luxun", "鲁迅说", "鲁迅")
  .category("meme_word")
  .brief("我没说过这句话")
  .usage("/鲁迅说 <文本>")
  .build()
)
@luxun.handle()
async def handle_luxun(args: Message = CommandArg()):
  def make() -> MessageSegment:
    content = args.extract_plain_text().rstrip() or luxun.__doc__ or ""
    im = Image.open(DIR / "template.jpg")
    text_im = textutil.render(content, "sans", 38, color=(255, 255, 255), align="m", spacing=5)
    text_im = imutil.contain_down(text_im, 440, 100)
    imutil.paste(im, text_im, (240, 350), anchor="mm")
    textutil.paste(im, (320, 400), "——鲁迅", "sans", 30, color=(255, 255, 255))
    return imutil.to_segment(im)
  await luxun.finish(await asyncio.to_thread(make))
