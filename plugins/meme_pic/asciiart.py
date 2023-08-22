from argparse import Namespace
from io import StringIO
from typing import List

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, imutil, misc, textutil
from util.user_aliases import AvatarGetter, DefaultType

PALETTE = {
  255: " ", 226: "`", 222: ".", 214: "-", 213: "'", 203: "^", 199: ",", 190: ":", 189: "~",
  176: "+", 173: "=", 170: "!", 168: "<", 166: ";", 160: "r", 157: "*", 145: "1", 136: "L",
  134: "/", 131: "7", 128: "i", 126: "?", 125: "c", 123: "(", 121: "x", 120: "z", 119: "J",
  115: "F", 114: "Y", 113: "f", 111: "n", 110: "y", 108: "I", 107: "4", 103: "o", 102: "j",
  101: "w", 100: "{", 98: "C", 92: "Z", 90: "2", 89: "a", 88: "V", 87: "[", 85: "h", 83: "3",
  82: "9", 81: "6", 80: "E", 77: "X", 72: "A", 68: "5", 67: "b", 64: "K", 55: "G", 53: "H",
  52: "m", 51: "O", 44: "D", 41: "R", 40: "8", 37: "W", 29: "&", 27: "B", 25: "0", 24: "Q",
  23: "#", 21: "N", 12: "M", 4: "%", 0: "@",
}
PALETTE_KEYS = list(PALETTE)
PALETTE_IM = Image.new("P", (0, 0))
PALETTE_IM.putpalette(b"".join(i.to_bytes(1, "little") * 3 for i in PALETTE_KEYS))
SIZE = 10
SCALE = 0.2


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接（可传入动图）"
))
group = parser.add_mutually_exclusive_group()
group.add_argument(
  "--webp", "-w", action="store_const", dest="format", const="webp", default="gif",
  help="使用WebP而非GIF格式（如果传入动图）"
)
group.add_argument(
  "--png", "--apng", "-p", action="store_const", dest="format", const="png",
  help="使用APNG而非GIF格式（如果传入动图）"
)
matcher = (
  command.CommandBuilder("meme_pic.asciiart", "字符画")
  .category("meme_pic")
  .brief("[动]")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, DefaultType.TARGET, raw=True)

  def make() -> MessageSegment:
    w, h = textutil.layout("A", "monospace", SIZE).get_size()
    aspect_ratio = w / h
    target, _ = target_task.result()
    frames: List[Image.Image] = []
    for raw in imutil.frames(target):
      columns = int(raw.width * SCALE)
      rows = int(raw.height * aspect_ratio * SCALE)
      mapped = imutil.quantize(
        imutil.background(raw).resize((columns, rows), imutil.scale_resample()), PALETTE_IM
      )
      px = mapped.load()
      lines = []
      for y in range(mapped.height):
        buf = StringIO()
        for x in range(mapped.width):
          buf.write(PALETTE[PALETTE_KEYS[px[x, y]]])
        lines.append(buf.getvalue())

      text_im = textutil.render("\n".join(lines), "monospace", SIZE)
      result = Image.new("L", text_im.size, 255)
      result.paste(text_im, mask=text_im)
      frames.append(result)
    return imutil.to_segment(frames, target, afmt=args.format)

  await matcher.finish(await misc.to_thread(make))
