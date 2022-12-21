from pathlib import Path

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image

from util import command, imutil, misc, textutil

DIR = Path(__file__).resolve().parent


prison = (
  command.CommandBuilder("meme_word.prison", "坐牢")
  .category("meme_word")
  .usage("/坐牢 <文本>")
  .build()
)
@prison.handle()
async def handle_prison(args: Message = CommandArg()):
  text = args.extract_plain_text().rstrip()
  if not text:
    await prison.finish(prison.__doc__)

  def make() -> MessageSegment:
    template = Image.open(DIR / "template.png")
    text_im = textutil.render(text, "sans", 35, box=template.width * 2 + 108, align="m")
    size = (max(template.width + 64, text_im.width + 20), 24 + template.height + text_im.height)
    im = Image.new("RGB", size, (255, 255, 255))
    imutil.paste(im, template, (im.width // 2, 24), anchor="mt")
    imutil.paste(im, text_im, (im.width // 2, template.height + 24), anchor="mt")
    return imutil.to_segment(im)

  await prison.finish(await misc.to_thread(make))
