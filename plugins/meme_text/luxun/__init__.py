import os
from io import BytesIO

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image

from util import command, text

plugin_dir = os.path.dirname(os.path.abspath(__file__))

USAGE = "/鲁迅说 <文本>"
addict = (
  command.CommandBuilder("meme_text.luxun", "鲁迅说", "鲁迅")
  .brief("我没说过这句话")
  .usage(USAGE)
  .build())


@addict.handle()
async def handle_addict(args: Message = CommandArg()):
  lines = args.extract_plain_text().rstrip().splitlines()
  if not lines:
    lines = [USAGE]
  elif len(lines) > 2:
    lines = ["最多只能有两行"]

  content = "\n".join(lines)
  im = Image.open(os.path.join(plugin_dir, "template.jpg"))
  text.paste(
    im, (240, 350), content, "sans", 38, color=(255, 255, 255), anchor="mm", align="m", spacing=5)
  text.paste(im, (320, 400), "——鲁迅", "sans", 30, color=(255, 255, 255))

  f = BytesIO()
  im.save(f, "png")
  await addict.send(MessageSegment.image(f))
