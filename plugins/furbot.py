import os
from typing import ClassVar, Tuple

import nonebot
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment
from nonebot.params import CommandArg, EventMessage

from util import command, context, help, misc, permission
from util.api_common import furbot

HEADER = "======== 绒狸 ========"
USAGE_BASE = '''\
/绒狸 - 发送随机毛图
/绒狸 [名字或ID] - 发送指定毛图
内容来自绒狸 API，官方群：893579624'''
USAGE_KEYWORD = "也可以使用关键词“{}”触发"
SUBMIT_IMAGE_URL = "https://s2.loli.net/2022/04/12/kpaO594er6RXQ7D.jpg"
SUBMIT_IMAGE_CACHE = "states/furbot_submit_image.jpg"

IDHAGN_NAMES = {"idhagn", "伊哈根", "su226"}
IDHAGN_EASTER_EGG = "你觉得我有毛吗（）"
EASTER_EGG_1 = (
  '''\
--- 每旤吶毘 =im ---
IC：Access Denied
毛毚吋孔：绒狸
搜紡斷泒：/* compiled code */
'''
  + MessageSegment.image("https://cdn.furryfan.cn/bot/avatar.png")
  + "\n--- root@FurryAir ---"
)
EASTER_EGG_2 = "搜紡绑枙：Access Denied\n--- root@FurryAir ---"


async def fetch_submit_image() -> MessageSegment:
  # 考虑到 loli.net 在国内较慢，增加缓存
  if not os.path.exists(SUBMIT_IMAGE_CACHE):
    http = misc.http()
    async with http.get(SUBMIT_IMAGE_URL) as response:
      with open(SUBMIT_IMAGE_CACHE, "wb") as f:
        f.write(await response.read())
  return misc.local("image", SUBMIT_IMAGE_CACHE)


class Source:
  name: ClassVar[str] = "绒狸"
  node: ClassVar[Tuple[str, ...]] = ("furbot", "picture", "keyword")

  @staticmethod
  def keyword() -> str:
    return furbot.CONFIG().keyword

  @staticmethod
  def available() -> bool:
    return bool(furbot.CONFIG().token)

  @staticmethod
  async def handle(bot: Bot, event: Event, args: str) -> None:
    if args.lower() in IDHAGN_NAMES:
      await bot.send(event, IDHAGN_EASTER_EGG)
      return
    if args == "绒狸":
      await bot.send(event, EASTER_EGG_1)
      return
    if not args:
      coro = furbot.get_random()
    else:
      try:
        id = int(args)
      except ValueError:
        coro = furbot.get_by_name(args)
      else:
        coro = furbot.get_by_id(id)
    try:
      pic = await coro
    except furbot.FurbotException as e:
      message = f"{HEADER}\n{e.message}"
      if e.code == 404:
        message += "\n你可以前往小程序投稿" + await fetch_submit_image()
      await bot.send(event, message)
      return
    header = f"{HEADER}\nID: {pic.cid or pic.id}\n名字: {pic.name}"
    await bot.send(event, header + MessageSegment.image(pic.url))
furbot.universal_sources["furbot"] = Source


def help_condition(_) -> bool:
  return Source.available()


def picture_usage() -> str:
  config = furbot.CONFIG()
  usage = USAGE_BASE
  if config.keyword:
    usage += "\n" + USAGE_KEYWORD.format(config.keyword)
  return usage
picture = (
  command.CommandBuilder("furbot.picture", "绒狸")
  .category("furbot")
  .brief("使用绒狸API的随机兽图")
  .usage(picture_usage)
  .help_condition(help_condition)
  .rule(Source.available)
  .build()
)
@picture.handle()
async def handle_picture(bot: Bot, event: Event, message: Message = CommandArg()):
  await Source.handle(bot, event, message.extract_plain_text().rstrip())


async def keyword_rule(message: Message = EventMessage()) -> bool:
  config = furbot.CONFIG()
  if not config.token or not config.keyword:
    return False
  seg = message[0]
  return seg.is_text() and str(seg).lstrip().startswith(config.keyword)
keyword = nonebot.on_message(
  keyword_rule,
  context.build_permission(Source.node, permission.Level.MEMBER),
  block=True
)
@keyword.handle()
async def handle_regex(bot: Bot, event: Event, message: Message = EventMessage()):
  config = furbot.CONFIG()
  args = misc.removeprefix(message.extract_plain_text().lstrip(), config.keyword)
  await Source.handle(bot, event, args.strip())


query = (
  command.CommandBuilder("furbot.query", "绒狸查询")
  .category("furbot")
  .brief("查询毛毛的绒狸FID")
  .usage("/绒狸查询 [名字]")
  .help_condition(help_condition)
  .rule(Source.available)
  .build()
)
@query.handle()
async def handle_query(message: Message = CommandArg()):
  args = message.extract_plain_text().strip()
  if not args:
    await query.finish(picture_usage())
  if args.lower() in IDHAGN_NAMES:
    await query.finish(IDHAGN_EASTER_EGG)
  if args == "绒狸":
    await query.finish(EASTER_EGG_2)
  try:
    name, ids = await furbot.query_id(args)
  except furbot.FurbotException as e:
    await query.finish(f"{HEADER}\n{e.message}")
  if not ids:
    img = await fetch_submit_image()
    await query.finish(f"{HEADER}\n没有查询到这只毛毛，你可以前往小程序投稿" + img)
  ids_str = "、".join(str(id) for id in ids)
  await query.finish(f"{HEADER}\n查询结果\n名字：{name}\nID：{ids_str}")


submit = (
  command.CommandBuilder("furbot.submit", "绒狸投稿")
  .category("furbot")
  .brief("向绒狸投稿毛毛")
  .help_condition(help_condition)
  .rule(Source.available)
  .build()
)
@submit.handle()
async def handle_submit():
  await submit.finish(f"{HEADER}\n请前往小程序投稿" + await fetch_submit_image())


daily = (
  command.CommandBuilder("furbot.daily", "每日鉴毛")
  .category("furbot")
  .brief("绒狸每日鉴毛")
  .usage('''\
/每日鉴毛 - 随机一期每日鉴毛
/每日鉴毛 <名字> - 指定毛毛的每日鉴毛
/每日鉴毛 <ID> - 指定ID的每日鉴毛''')
  .help_condition(help_condition)
  .rule(Source.available)
  .build()
)
@daily.handle()
async def handle_daily(bot: Bot, event: Event, message: Message = CommandArg()):
  args = message.extract_plain_text().rstrip()
  if not args:
    coro = furbot.get_daily_random()
  if args.lower() in IDHAGN_NAMES:
    await query.finish(IDHAGN_EASTER_EGG)
  if args == "绒狸":
    await query.finish(EASTER_EGG_1)
  if not args:
    coro = furbot.get_daily_random()
  else:
    try:
      id = int(args)
    except ValueError:
      coro = furbot.get_daily_by_name(args)
    else:
      coro = furbot.get_daily_by_id(id)
  try:
    pic = await coro
  except furbot.FurbotException as e:
    await bot.send(event, f"{HEADER}\n{e.message}")
    return
  header = f"{HEADER}\nID: {pic.cid or pic.id}\n名字: {pic.name}"
  await bot.send(event, header + MessageSegment.image(pic.url))


furbot.register_universal_keyword()

category = help.CategoryItem.find("furbot")
category.data.node_str = "furbot"
category.data.condition = help_condition
category.brief = "绒狸"
category.add(help.StringItem("绒狸官方群：893579624"))
