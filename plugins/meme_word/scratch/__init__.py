from pathlib import Path

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image

from util import command, imutil, misc, textutil

DIR = Path(__file__).resolve().parent


scratch = (
  command.CommandBuilder("meme_word.scratch", "刮刮乐")
  .category("meme_word")
  .usage("/刮刮乐 <文本>")
  .build()
)
@scratch.handle()
async def handle_not_call_me(args: Message = CommandArg()):
  text = args.extract_plain_text().rstrip()
  if not text:
    await scratch.finish(scratch.__doc__)

  def make() -> MessageSegment:
    text_im = textutil.render(text, "sans", 80, color=(255, 255, 255), box=420, align="m")
    text_im = imutil.contain_down(text_im, 280, 130)
    im = Image.open(DIR / "template.png")
    imutil.paste(im, text_im, (220, 225), anchor="mm")
    overlay = Image.open(DIR / "overlay.png")
    im.paste(overlay, mask=overlay)
    return imutil.to_segment(im)

  await scratch.finish(await misc.to_thread(make))
