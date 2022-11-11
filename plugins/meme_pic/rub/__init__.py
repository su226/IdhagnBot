import asyncio
from argparse import Namespace
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, imutil
from util.user_aliases import AvatarGetter

DIR = Path(__file__).resolve().parent
BOXES = [(25, 66), (25, 66), (23, 68), (20, 69), (22, 68), (25, 66)]


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
group = parser.add_mutually_exclusive_group()
group.add_argument(
  "--webp", "-w", action="store_const", dest="format", const="webp", default="gif",
  help="使用WebP而非GIF格式"
)
group.add_argument(
  "--png", "--apng", "-p", action="store_const", dest="format", const="png",
  help="使用APNG而非GIF格式"
)
matcher = (
  command.CommandBuilder("meme_pic.rub", "搓")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, event.self_id)

  def make() -> MessageSegment:
    target, _ = target_task.result()
    frames: list[Image.Image] = []
    target = target.resize((78, 78), imutil.scale_resample())
    for i in range(5):
      template = Image.open(DIR / f"{i}.png")
      frame = Image.new("RGB", template.size, (255, 255, 255))
      target1 = target.rotate(i / 5 * 360)
      frame.paste(target1, BOXES[i], target1)
      frame.paste(template, mask=template)
      frames.append(frame)
    return imutil.to_segment(frames, 100, afmt=args.format)

  await matcher.finish(await asyncio.to_thread(make))
