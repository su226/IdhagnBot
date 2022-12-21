from pathlib import Path

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image

from util import command, imutil, misc, textutil

DIR = Path(__file__).resolve().parent


wakeup = (
  command.CommandBuilder("meme_word.wakeup", "起来了")
  .category("meme_word")
  .usage("/起来了 <文本>")
  .build()
)
@wakeup.handle()
async def handle_wakeup(args: Message = CommandArg()):
  text = args.extract_plain_text().rstrip()
  if not text:
    await wakeup.finish(wakeup.__doc__)

  def make() -> MessageSegment:
    im = Image.open(DIR / "template.jpg")
    text_im = textutil.render(text, "sans", 75)
    text_im = imutil.contain_down(text_im, 150, 110)
    imutil.paste(im, text_im, (385, 325), anchor="mm")
    text_im = textutil.render(f"{text}起来了", "sans", 96)
    text_im = imutil.contain_down(text_im, 650, 144)
    imutil.paste(im, text_im, (360, 667), anchor="mm")
    return imutil.to_segment(im)

  await wakeup.finish(await misc.to_thread(make))
