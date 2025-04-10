from pathlib import Path

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image

from util import command, imutil, misc, textutil

DIR = Path(__file__).resolve().parent


addict = (
  command.CommandBuilder("memes.addict", "成瘾前后", "成瘾")
  .category("memes")
  .brief("会露出笑容")
  .usage("/成瘾 <文本>")
  .build()
)
@addict.handle()
async def handle_addict(args: Message = CommandArg()):
  content = args.extract_plain_text().rstrip()
  if not content:
    await addict.finish(addict.__doc__)

  def make() -> MessageSegment:
    im = Image.open(DIR / "template.png")
    text_im = textutil.render(content, "sans medium", 50, color=(255, 255, 255))
    text_im = imutil.contain_down(text_im, 290, 72)
    imutil.paste(im, text_im, (543, 684), anchor="mm")
    return imutil.to_segment(im)

  await addict.finish(await misc.to_thread(make))
