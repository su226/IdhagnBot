import asyncio
from argparse import Namespace
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageOps

from util import command, imutil
from util.user_aliases import AvatarGetter

DIR = Path(__file__).resolve().parent
# RemapTransform((330, 330), ((0, 19), (236, 0), (287, 264), (66, 351)))  # noqa
OLD_SIZE = 330, 330
NEW_SIZE = 287, 351
TRANSFORM = (
  1.0952291221755943, -0.2177262712758823, 4.1367991542420945, 0.07837100517494805,
  0.9734503800677476, -18.49555722128834, -0.0008652944018017274, 0.00014852909086833315
)


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
  command.CommandBuilder("meme_pic.prpr", "舔", "舔屏", "prpr")
  .category("meme_pic")
  .brief("[动]少舔屏，小心屏幕进水")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, event.self_id, raw=True)

  def make() -> MessageSegment:
    target, _ = target_task.result()
    template = Image.open(DIR / "template.png")
    frames: list[Image.Image] = []
    for raw in imutil.frames(target):
      frame = ImageOps.fit(raw.convert("RGBA"), OLD_SIZE, imutil.scale_resample())
      frame = frame.transform(NEW_SIZE, Image.Transform.PERSPECTIVE, TRANSFORM, imutil.resample())
      im = Image.new("RGB", template.size, (0, 0, 0))
      im.paste(frame, (56, 284), frame)
      im.paste(template, mask=template)
      frames.append(im)
    return imutil.to_segment(frames, target, afmt=args.format)

  await matcher.finish(await asyncio.to_thread(make))
