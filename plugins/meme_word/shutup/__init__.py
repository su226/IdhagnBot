from pathlib import Path

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image

from util import command, imutil, misc, textutil

DIR = Path(__file__).resolve().parent


shutup = (
  command.CommandBuilder("meme_word.shutup", "别说了")
  .category("meme_word")
  .usage("/别说了 <文本>")
  .build()
)
@shutup.handle()
async def handle_shutup(args: Message = CommandArg()):
  text = args.extract_plain_text().rstrip()
  if not text:
    await shutup.finish(shutup.__doc__)

  def make() -> MessageSegment:
    template = Image.open(DIR / "template.png")
    text_im = textutil.render(text, "sans", 40, box=template.width * 2 - 20, align="m")
    size = (max(template.width, text_im.width + 20), 15 + template.height + text_im.height)
    im = Image.new("RGB", size, (255, 255, 255))
    imutil.paste(im, template, (im.width // 2, 15), anchor="mt")
    imutil.paste(im, text_im, (im.width // 2, template.height + 15), anchor="mt")
    return imutil.to_segment(im)

  await shutup.finish(await misc.to_thread(make))
