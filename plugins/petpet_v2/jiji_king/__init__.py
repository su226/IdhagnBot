import asyncio
import itertools
from argparse import Namespace
from pathlib import Path
from typing import Awaitable

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageOps

from util import command, text, util

from ..util import get_image_and_user

DIR = Path(__file__).resolve().parent
BRACKETS = [  # 所有形式的大括号、中括号、小括号、尖括号，来自中州韵输入法（）
  "{}", "『』", "〖〗", "｛｝", "[]", "「」", "【】", "〔〕", "［］", "〚〛", "〘〙", "()", "（）",
  "<>", "《》", "〈〉", "«»", "‹›", "⟨⟩"
]

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="*", default=[], metavar="目标",
  help="可使用@、QQ号、昵称、群名片或图片链接，或者用括号包起来的字符（最多10个）"
)
parser.add_argument(
  "--text", "-t", default="我是急急国王", metavar="文本",
  help="默认为“我是急急国王”"
)
parser.add_argument(
  "--source", "-s", default="", metavar="源",
  help="可使用@、QQ号、昵称、群名片或图片链接，或者用括号包起来的字符"
)

matcher = command.CommandBuilder("petpet_v2.jiji_king", "急急国王") \
  .category("petpet_v2") \
  .shell(parser) \
  .auto_reject() \
  .build()
@matcher.handle()
async def handler(
  bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()
) -> None:
  async def get_avatar(pattern: str, default: int, size: int) -> Image.Image:
    for left, right in BRACKETS:
      if pattern.startswith(left) and pattern.endswith(right):
        return await asyncio.to_thread(make_char, pattern[1:-1], size)
    avatar, _ = await get_image_and_user(bot, event, pattern, default)
    return await asyncio.to_thread(avatar.resize, (size, size), util.scale_resample)

  def make_char(char: str, size: int) -> Image.Image:
    fg = text.render(char, "sans bold", size * 0.67, color=(255, 255, 255))
    fg = ImageOps.pad(fg, (size, size), util.resample)
    im = Image.new("RGB", fg.size)
    im.paste(fg, mask=fg)
    return im

  if len(args.target) > 10:
    await matcher.finish("最多只能有 10 个目标")
  coros: list[Awaitable[Image.Image]] = [get_avatar(args.source, event.user_id, 125)]
  if not args.target:
    args.target.append("")
  for pattern in args.target:
    coros.append(get_avatar(pattern, event.self_id, 90))
  try:
    source, *target = await asyncio.gather(*coros)
  except util.AggregateError as e:
    await matcher.finish("\n".join(e))

  def make() -> MessageSegment:
    block_count = max(5, len(target))
    im = Image.new("RGB", (10 + block_count * 100, 400), (255, 255, 255))
    template = Image.open(DIR / "template.png")
    x = (im.width - template.width) // 2
    util.paste(im, template, (x, 6))
    util.paste(im, source, (x + 237, 5))

    repeat = [block_count // len(target)] * len(target)
    for i in range(block_count % len(target)):
      repeat[i] += 1
    blocks = list(itertools.chain.from_iterable([im] * count for im, count in zip(target, repeat)))

    for i, block in enumerate(blocks):
      im.paste(block, (10 + i * 100, 200))

    text_im = text.render(args.text, "sans bold", 60)
    text_im = util.contain_down(text_im, im.width - 10, 90)
    util.paste(im, text_im, (im.width // 2, 345), anchor="mm")

    return util.pil_image(im)

  await matcher.finish(await asyncio.to_thread(make))
