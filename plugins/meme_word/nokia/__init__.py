from pathlib import Path

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image, ImageFilter, ImageOps

from util import command, imutil, misc, textutil

DIR = Path(__file__).resolve().parent


nokia = (
  command.CommandBuilder("meme_word.nokia", "诺基亚", "nokia", "无内鬼")
  .category("meme_word")
  .brief("无内鬼，来点涩图")
  .usage('''\
/诺基亚 <文本>
自动换行，文本不能超过 7 行''')
  .build()
)
@nokia.handle()
async def handle_nokia(args: Message = CommandArg()):
  def make() -> MessageSegment:
    content = misc.removeprefix(args.extract_plain_text().rstrip(), ".") or nokia.__doc__ or ""
    font = textutil.special_font("pixel", "sans")
    layout = textutil.layout(content, font, 32, box=320)
    if layout.get_pixel_size().height > 224:
      layout = textutil.layout("文本不能超过 7 行", font, 32, box=320)
    layer = textutil.render(layout, color=(24, 53, 4))
    layer = ImageOps.expand(layer, (0, 0, 320 - layer.width, 224 - layer.height))
    layer = layer.rotate(-14, imutil.resample(), True)
    layer = layer.filter(ImageFilter.GaussianBlur(0.75))
    im = Image.open(DIR / "template.png")
    im.paste(layer, (83, 127), layer)
    return imutil.to_segment(im)
  await nokia.finish(await misc.to_thread(make))
