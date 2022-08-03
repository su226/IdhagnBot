import os
from io import BytesIO

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image, ImageFilter, ImageOps

from util import command, text, util

plugin_dir = os.path.dirname(os.path.abspath(__file__))
HELP = '''\
/诺基亚 <文本>
自动换行，文本不能超过 7 行'''

nokia = (
  command.CommandBuilder("meme_text.nokia", "诺基亚", "nokia", "无内鬼")
  .brief("生成诺基亚无内鬼梗图")
  .usage(HELP)
  .build())


@nokia.handle()
async def handle_nokia(args: Message = CommandArg()):
  content = args.extract_plain_text().rstrip().removeprefix(".") or f"用法:\n{HELP}"
  font = util.special_font("pixel", "sans")
  layout = text.layout(content, font, 32, box=320)
  if layout.get_pixel_size().height > 224:
    layout = text.layout("文本不能超过 7 行", font, 32, box=320)
  layer = text.render(layout, color=(24, 53, 4))
  layer = ImageOps.expand(layer, (0, 0, 320 - layer.width, 224 - layer.height))
  layer = layer.rotate(-14, util.resample, True)
  layer = layer.filter(ImageFilter.GaussianBlur(0.75))
  im = Image.open(os.path.join(plugin_dir, "诺基亚.png"))
  im.paste(layer, (83, 127), layer)
  f = BytesIO()
  im.save(f, "png")
  await nokia.send(MessageSegment.image(f))
