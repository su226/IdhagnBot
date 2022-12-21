from pathlib import Path

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image

from util import command, imutil, misc, textutil

DIR = Path(__file__).resolve().parent


bronya = (
  command.CommandBuilder("meme_word.bronya", "大鸭鸭举牌")
  .category("meme_word")
  .usage("/大鸭鸭举牌 <文本>")
  .build()
)
@bronya.handle()
async def handle_bronya(args: Message = CommandArg()):
  def make() -> MessageSegment:
    text = args.extract_plain_text().rstrip() or bronya.__doc__ or ""
    im = Image.open(DIR / "template.jpg")
    text_im = textutil.render(text, "sans", 60, box=675, color=(111, 95, 95), align="m")
    text_im = imutil.contain_down(text_im, 450, 255)
    imutil.paste(im, text_im, (415, 802), anchor="mm")
    return imutil.to_segment(im)
  await bronya.finish(await misc.to_thread(make))
