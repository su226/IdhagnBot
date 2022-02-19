from io import BytesIO
from PIL import Image, ImageDraw, ImageFilter
from util import resources
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
import os
import nonebot

plugin_dir = os.path.dirname(os.path.abspath(__file__))
HELP = '''\
/诺基亚 <文本>
自动换行，文本不能超过 6 行'''

nokia = nonebot.on_command("诺基亚", aliases={"nokia", "无内鬼"})
nokia.__cmd__ = ["诺基亚", "nokia", "无内鬼"]
nokia.__brief__ = "生成诺基亚无内鬼梗图"
nokia.__doc__ = HELP
@nokia.handle()
async def handle_nokia(args: Message = CommandArg()):
  text = args.extract_plain_text().replace("\r", "").rstrip().removeprefix(".") or f"用法:\n{HELP}"
  layer = Image.new("RGBA", (320, 224))
  draw = ImageDraw.Draw(layer)
  lines = []
  cur_line = ""
  font = resources.font("pixel", 32)
  for ch in text:
    if ch == "\n" or font.getsize(cur_line + ch)[0] > layer.width:
      lines.append(cur_line)
      cur_line = ""
    if ch != "\n":
      cur_line += ch
  if cur_line:
    lines.append(cur_line)
  if len(lines) > 7:
    lines = ["文本不能超过 7 行"]
  draw.text((0, 0), "\n".join(lines), (24, 53, 4), font)
  layer = layer.rotate(-14, Image.BICUBIC, True)
  layer = layer.filter(ImageFilter.GaussianBlur(0.75))
  im = Image.open(os.path.join(plugin_dir, "诺基亚.png"))
  im.paste(layer, (83, 127), layer)
  f = BytesIO()
  im.save(f, "png")
  await nokia.send(MessageSegment.image(f))
