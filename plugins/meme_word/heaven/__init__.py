from pathlib import Path

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image

from util import command, imutil, misc, textutil

DIR = Path(__file__).resolve().parent


heaven = (
  command.CommandBuilder("meme_word.heaven", "升天")
  .category("meme_word")
  .usage("/升天 <文本>")
  .build()
)
@heaven.handle()
async def handle_not_call_me(args: Message = CommandArg()):
  text = args.extract_plain_text().rstrip()
  if not text:
    await heaven.finish(heaven.__doc__)

  def make() -> MessageSegment:
    nonlocal text
    text = f"你原本应该要去地狱的，但因为你生前{text}，我们就当作你已经服完刑期了"
    text_im = textutil.render(text, "sans", 25, box=446, align="m")
    text_im = imutil.contain_down(text_im, 446, 108)
    im = Image.open(DIR / "template.png")
    imutil.paste(im, text_im, (263, 82), anchor="mm")
    return imutil.to_segment(im)

  await heaven.finish(await misc.to_thread(make))
