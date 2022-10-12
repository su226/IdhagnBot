from argparse import Namespace
from io import BytesIO, StringIO
from pathlib import Path
from typing import cast

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, PyAccess

from util import command, text, util

from ..util import get_image_and_user, segment_animated_image

plugin_dir = Path(__file__).resolve().parent
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
_w, _h = text.layout("A", "monospace", SIZE).get_size()
ASPECT_RATIO = _w / _h
del _w, _h

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标",
  help="可使用@、QQ号、昵称、群名片或图片链接（可传入动图）")
group = parser.add_mutually_exclusive_group()
group.add_argument(
  "--webp", "-w", action="store_const", dest="format", const="webp", default="gif",
  help="使用WebP而非GIF格式（如果传入动图）")
group.add_argument(
  "--png", "--apng", "-p", action="store_const", dest="format", const="png",
  help="使用APNG而非GIF格式（如果传入动图）")
matcher = (
  command.CommandBuilder("petpet_v2.asciiart", "字符画")
  .category("petpet_v2")
  .brief("[动]")
  .shell(parser)
  .build())


@matcher.handle()
async def handler(
  bot: Bot, event: MessageEvent, args: Namespace | ParserExit = ShellCommandArgs()
) -> None:
  if isinstance(args, ParserExit):
    await matcher.finish(args.message)
  try:
    avatar, _ = await get_image_and_user(bot, event, args.target, event.self_id, raw=True)
  except util.AggregateError as e:
    await matcher.finish("\n".join(e))

  frames: list[Image.Image] = []
  frametime = avatar.info.get("duration", 0)
  for raw in util.frames(avatar):
    columns = int(raw.width * SCALE)
    rows = int(raw.height * ASPECT_RATIO * SCALE)
    scaled = raw.convert("RGBA").resize((columns, rows), util.scale_resample)
    mapped = Image.new("RGB", scaled.size, (255, 255, 255))
    mapped.paste(scaled, mask=scaled)
    mapped = mapped.quantize(256, Image.Dither.FLOYDSTEINBERG, palette=PALETTE_IM)  # type: ignore

    px = cast(PyAccess.PyAccess, mapped.load())
    lines = []
    for y in range(mapped.height):
      buf = StringIO()
      for x in range(mapped.width):
        buf.write(PALETTE[PALETTE_KEYS[px[x, y]]])
      lines.append(buf.getvalue())

    text_im = text.render("\n".join(lines), "monospace", SIZE)
    result = Image.new("L", text_im.size, 255)
    result.paste(text_im, mask=text_im)
    frames.append(result)

  if len(frames) > 1:
    segment = segment_animated_image(args.format, frames, frametime)
  else:
    f = BytesIO()
    frames[0].save(f, "png")
    segment = MessageSegment.image(f)
  await matcher.finish(segment)
