from argparse import Namespace

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.exception import ActionFailed
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, context, imutil, misc, textutil
from util.user_aliases import AvatarGetter

GENDERS = {
  "male": "他",
  "female": "她",
  "unknown": "它",
  "animal": "牠",
  "god": "祂",
}


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
  command.CommandBuilder("meme_pic.angel", "小天使")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, event.self_id)
  target, target_id = target_task.result()
  name = args.name
  gender = args.gender
  if (name is None or gender is None) and target_id is not None:
    try:
      info = await bot.get_group_member_info(
        group_id=context.get_event_context(event), user_id=target_id
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
    im = Image.new("RGB", (600, 730), (255, 255, 255))

    im2 = textutil.render(f"请问你们看到{name}了吗?", "sans bold", 70)
    im2 = imutil.contain_down(im2, 560, 100)
    imutil.paste(im, im2, (300, 55), anchor="mm")

    nonlocal target
    target = target.resize((500, 500), imutil.scale_resample())
    im.paste(target, (50, 110), target)

    textutil.paste(
      im, (300, 610), "非常可爱！简直就是小天使",
      "sans bold", 48, anchor="mt"
    )
    textutil.paste(
      im, (300, 680), f"{GENDERS[gender]}没失踪也没怎么样  我只是觉得你们都该看一下",
      "sans bold", 26, anchor="mt"
    )

    return imutil.to_segment(im)

  await matcher.finish(await misc.to_thread(make))
