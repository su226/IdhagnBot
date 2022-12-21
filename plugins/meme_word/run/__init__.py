from pathlib import Path

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image

from util import command, imutil, misc, textutil

DIR = Path(__file__).resolve().parent


run = (
  command.CommandBuilder("meme_word.run", "快跑")
  .category("meme_word")
  .usage("/快跑 <文本>")
  .build()
)
@run.handle()
async def handle_not_call_me(args: Message = CommandArg()):
  text = args.extract_plain_text().rstrip()
  if not text:
    await run.finish(run.__doc__)

  def make() -> MessageSegment:
    text_im = textutil.render(text, "sans", 35, box=183, align="m")
    text_im = imutil.center_pad(text_im, 122, 53)
    text_im = text_im.rotate(7, imutil.resample(), True)
    im = Image.open(DIR / "template.png")
    im.paste(text_im, (200, 195), text_im)
    return imutil.to_segment(im)

  await run.finish(await misc.to_thread(make))
