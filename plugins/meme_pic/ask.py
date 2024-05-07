from argparse import Namespace
from typing import Tuple, Union, overload

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.exception import ActionFailed
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, context, imutil, misc, textutil
from util.user_aliases import AvatarGetter, DefaultType

GENDERS = {
  "male": "他",
  "female": "她",
  "unknown": "它",
  "animal": "牠",
  "god": "祂",
}


@overload
def vertical_gradient(
  mode: str, top: int, bottom: int, width: int, height: int,
) -> Image.Image: ...

@overload
def vertical_gradient(
  mode: str, top: Tuple[int, ...], bottom: Tuple[int, ...], width: int, height: int,
) -> Image.Image: ...

def vertical_gradient(
  mode: str, top: Union[int, Tuple[int, ...]], bottom: Union[int, Tuple[int, ...]], width: int,
  height: int,
) -> Image.Image:
  gradient = Image.new(mode, (1, height))
  px = gradient.load()
  if isinstance(bottom, tuple) and isinstance(top, tuple):
    delta = tuple(x - y for x, y in zip(bottom, top))
    for i in range(height):
      ratio = i / (height - 1)
      px[0, i] = tuple(int(ratio * x + y) for x, y in zip(delta, top))
  elif isinstance(bottom, int) and isinstance(top, int):
    delta = bottom - top
    for i in range(height):
      px[0, i] = int(delta * (i / (height - 1))) + top
  else:
    raise TypeError
  return gradient.resize((width, height))


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
parser.add_argument("--name", "-n", metavar="名字", help=(
  "自定义名字，对于图片链接必须指定，对于QQ用户默认使用昵称"
))
parser.add_argument("--gender", "-g", choices=GENDERS, metavar="性别", help=(
  "自定义性别，对于图片链接默认为未知，对于QQ用户默认为资料性别，"
  "可以是“male”（他）、“female”（她）、“unknown”（它）、“animal”（牠）、“god”（祂）"
))
matcher = (
  command.CommandBuilder("meme_pic.ask", "问", "问问")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, DefaultType.TARGET)
  target, target_id = target_task.result()
  name = args.name
  gender = args.gender
  if (name is None or gender is None) and target_id is not None:
    try:
      info = await bot.get_group_member_info(
        group_id=context.get_event_context(event), user_id=target_id,
      )
      name = name or info["card"] or info["nickname"]
      gender = gender or info["sex"]
    except ActionFailed:
      info = await bot.get_stranger_info(user_id=target_id)
      name = name or info["nickname"]
      gender = gender or info["sex"]
  if gender is None:
    gender = "unknown"
  if name is None:
    await matcher.finish("请使用 --name 指定名字")

  def make() -> MessageSegment:
    nonlocal target
    target = target.resize((640, 640), imutil.scale_resample())
    gradient_h = 150
    padding_x = 30
    padding_y = 80
    text_x = padding_x + 30
    text_y = padding_y + target.height - gradient_h

    im = Image.new(
      "RGB", (target.width + padding_x * 2, target.height + padding_y * 2), (255, 255, 255),
    )
    im.paste(target, (padding_x, padding_y), target)
    im.paste(
      (0, 0, 0), (padding_x, text_y), vertical_gradient("L", 192, 128, target.width, gradient_h),
    )

    textutil.paste(im, (padding_x, padding_y // 2), f"让{name}告诉你吧", "sans", 35, anchor="lm")
    text_im = textutil.paste(im, (text_x, text_y + 5), name, "sans bold", 25, color=(255, 165, 0))
    im.paste((255, 165, 0), (text_x - 5, text_y + 45, text_x + text_im.width + 5, text_y + 47))
    textutil.paste(
      im, (text_x, text_y + 50), f"{name}不知道哦", "sans bold", 25, color=(255, 255, 255),
    )
    textutil.paste(
      im, (padding_x, target.height + padding_y + padding_y // 2),
      f"啊这，{GENDERS[gender]}说不知道", "sans", 35, anchor="lm",
    )

    return imutil.to_segment(im)

  await matcher.finish(await misc.to_thread(make))
