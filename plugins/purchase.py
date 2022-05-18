from argparse import Namespace
import asyncio
import itertools
import random

from pydantic import BaseModel, Field
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, Message, MessageSegment
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs, CommandArg, ArgPlainText
from nonebot.rule import ArgumentParser
from nonebot.typing import T_State

from util import context, account_aliases, currency, helper, command
from util.config import BaseState

class Goods(BaseModel):
  notify: int
  name: str
  description: str
  price: int
  total: int
  single: int
  disabled: bool = False
  total_purchased: int = 0
  single_purchased: dict[int, int] = Field(default_factory=dict)

class State(BaseState, file="goods"):
  goods: dict[int, dict[int, Goods]] = Field(default_factory=dict)

STATE = State.load()

parser_add_goods = ArgumentParser("/添加商品", add_help=False)
parser_add_goods.add_argument("name", metavar="商品名")
parser_add_goods.add_argument("price", metavar="价格", type=int)
parser_add_goods.add_argument("-desc", "-描述", metavar="内容", default="没有描述", help="商品描述，如果有空格或换行要用英文引号包起来")
parser_add_goods.add_argument("-total", "-总限购", metavar="次数", type=int, default=0, help="全部群成员可购买的次数，默认不限购")
parser_add_goods.add_argument("-single", "-单人限购", metavar="次数", type=int, default=0, help="每个群成员可购买的次数，默认不限购")
parser_add_goods.add_argument("-notify", "-提醒", metavar="用户", help="设置购买商品后提醒谁")
add_goods = (command.CommandBuilder("purchase.add_goods", "添加商品")
  .in_group()
  .level("admin")
  .brief("添加一个金币商品")
  .shell(parser_add_goods)
  .build())
@add_goods.handle()
async def handle_add_goods(bot: Bot, event: MessageEvent, args: Namespace | ParserExit = ShellCommandArgs()):
  if isinstance(args, ParserExit):
    await add_goods.finish(args.message)
  if args.notify is None:
    notify = event.user_id
  else:
    try:
      notify = await account_aliases.match_uid(bot, event, args.notify)
    except helper.AggregateError as e:
      await add_goods.finish("\n".join(e))
  ctx = context.get_event_context(event)
  goods = Goods(notify=notify, name=args.name, price=args.price, description=args.desc, total=args.total, single=args.single)
  goods_id = random.randrange(1000000000)
  if ctx not in STATE.goods:
    STATE.goods[ctx] = {}
  STATE.goods[ctx][goods_id] = goods
  STATE.dump()
  await add_goods.finish(f"已添加ID为 {goods_id} 的商品")

def find_goods(ctx: int, raw_pattern: str) -> tuple[int, Goods]:
  try:
    id = int(raw_pattern)
    return id, STATE.goods[ctx][id]
  except (ValueError, KeyError):
    pass
  pattern = account_aliases.to_identifier(raw_pattern)
  if not pattern:
    raise helper.AggregateError(f"有效名字为空：{raw_pattern}")
  all_goods = STATE.goods.get(ctx, {})
  exact: list[tuple[int, Goods]] = []
  inexact: list[tuple[int, Goods]] = []
  for id, goods in all_goods.items():
    ident = account_aliases.to_identifier(goods.name)
    if pattern == ident:
      exact.append((id, goods))
    elif pattern in ident:
      inexact.append((id, goods))
  all_goods = exact or inexact
  if not all_goods:
    raise helper.AggregateError(f"没有找到商品：{raw_pattern}")
  elif len(all_goods) > 1:
    segments = [f"{raw_pattern} 可以指多个商品，请使用更具体的名字或者商品ID："]
    for id, goods in itertools.chain(exact, inexact):
      if goods.disabled:
        price = "已下架"
      else:
        price = f"{goods.price}金币"
      segments.append(f"{id:09} - {goods.name}: {price}")
    raise helper.AggregateError("\n".join(segments))
  return all_goods[0]

async def find_user(bot: Bot, event: MessageEvent, pattern: str) -> int:
  if pattern == "全部":
    return 0
  return await account_aliases.match_uid(bot, event, pattern)

parser_modify_goods = ArgumentParser("/修改商品")
group = parser_modify_goods.add_argument_group()
parser_modify_goods.add_argument("goods", metavar="商品", help="可以是名字或ID")
parser_modify_goods.add_argument("-name", "-名字", metavar="新名字", help="修改商品名字，默认为不修改")
parser_modify_goods.add_argument("-desc", "-描述", metavar="新描述", help="修改商品描述，默认为不修改")
parser_modify_goods.add_argument("-price", "-价格", metavar="新价格", type=int, help="修改商品价格，默认为不修改")
parser_modify_goods.add_argument("-total", "-总限购", metavar="新次数", type=int, help="修改商品总限购，默认为不修改")
parser_modify_goods.add_argument("-single", "-单人限购", metavar="新次数", type=int, help="修改商品单人限购，默认为不修改")
parser_modify_goods.add_argument("-reset-total", "-重置总限购", action="store_true", help="重置总限购")
parser_modify_goods.add_argument("-reset-single", "-重置单人限购", metavar="用户", action="append", default=[], help="重置某人的单人限购（可使用多次），也可使用\"全部\"指定全部人")
parser_modify_goods.add_argument("-notify", "-提醒", metavar="新用户", help="设置购买商品后提醒谁")
parser_modify_goods.add_argument("-delete", "-删除", action="store_true", help="删除商品（不能找回）")
group = parser_modify_goods.add_mutually_exclusive_group()
group.add_argument("-disable", "-下架", dest="disabled", action="store_true", default=None, help="下架商品，不会隐藏商品，但是不能购买")
group.add_argument("-enable", "-上架", dest="disabled", action="store_false", help="重新上架商品")
modify_goods = (command.CommandBuilder("purchase.modify_goods", "修改商品")
  .in_group()
  .level("admin")
  .brief("修改一个金币商品")
  .shell(parser_modify_goods)
  .build())
@modify_goods.handle()
async def handle_modify_goods(bot: Bot, event: MessageEvent, args: Namespace | ParserExit = ShellCommandArgs()):
  if isinstance(args, ParserExit):
    await modify_goods.finish(args.message)
  ctx = context.get_event_context(event)
  try:
    id, goods = find_goods(ctx, args.goods)
  except helper.AggregateError as e:
    await modify_goods.finish("\n".join(e))
  coros = []
  for pattern in args.reset_single:
    coros.append(find_user(bot, event, pattern))
  errors, reset_single = [], []
  for i in await asyncio.gather(*coros, return_exceptions=True):
    if isinstance(i, helper.AggregateError):
      errors.extend(i)
    else:
      reset_single.append(i)
  if errors:
    await modify_goods.finish("\n".join(errors))
  notify = args.notify
  if notify is not None:
    try:
      notify = await account_aliases.match_uid(bot, event, args.notify)
    except helper.AggregateError as e:
      await modify_goods.finish("\n".join(e))
  results = []
  if args.name is not None:
    goods.name = args.name
    results.append(f"已修改商品名为：{args.name}")
  if args.desc is not None:
    goods.description = args.desc
    results.append(f"已修改描述为：{args.desc}")
  if args.price is not None:
    goods.price = args.price
    results.append(f"已修改价格为：{args.price}")
  if args.total is not None:
    goods.total = args.total
    results.append(f"已修改总限购为：{args.total}")
  if args.single is not None:
    goods.single = args.single
    results.append(f"已修改单人限购为：{args.single}")
  if args.reset_total:
    goods.total_purchased = 0
    results.append(f"已重置总限购")
  for i in reset_single:
    if i == 0:
      goods.single_purchased.clear()
      results.append(f"已重置所有人的单人限购")
    else:
      info = await bot.get_group_member_info(group_id=ctx, user_id=i)
      username = info["card"] or info["nickname"]
      if i in goods.single_purchased:
        del goods.single_purchased[i]
      results.append(f"已重置 {username} 的单人限购")
  if notify is not None:
    info = await bot.get_group_member_info(group_id=ctx, user_id=notify)
    username = info["card"] or info["nickname"]
    goods.notify = notify
    results.append(f"已修改提醒为：{username}（{notify}）")
  if args.disabled is not None:
    goods.disabled = args.disabled
    if args.disabled:
      results.append(f"已下架商品")
    else:
      results.append(f"已重新上架商品")
  if args.delete:
    del STATE.goods[ctx][id]
    results.append("已删除商品")
  if not results:
    results.append("似乎什么都没改")
  STATE.dump()
  await modify_goods.finish("\n".join(results))

async def format_goods(bot: Bot, event: MessageEvent, id: int, goods: Goods) -> Message:
  ctx = context.get_event_context(event)
  owner_info = await bot.get_group_member_info(group_id=ctx, user_id=goods.notify)
  owner_name = owner_info["card"] or owner_info["nickname"]
  if goods.disabled:
    name = "[已下架]" + goods.name
  else:
    name = goods.name
  if goods.total:
    total = f"{goods.total_purchased}/{goods.total}"
  else:
    total = f"{goods.total_purchased}"
  single_purchased = goods.single_purchased.get(event.user_id, 0)
  if goods.single:
    single = f"{single_purchased}/{goods.single}"
  else:
    single = f"{single_purchased}"
  return (
    f"{owner_name}（{goods.notify}）的商品\n"
    f"ID：{id:09}\n"
    f"名字：{name}\n"
    f"价格：{goods.price}金币\n"
    f"总计已购买：{total}\n"
    f"你已购买：{single}\n"
    f"简介："
  ) + Message(goods.description)
  
show_goods = (command.CommandBuilder("purchase.show_goods", "商品")
  .in_group()
  .brief("列出所有金币商品或显示详细信息")
  .usage('''\
/商品 - 列出所有金币商品
/商品 <名字或ID> - 显示商品详细信息''')
  .build())
@show_goods.handle()
async def handle_show_goods(bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
  name = arg.extract_plain_text().rstrip()
  ctx = context.get_event_context(event)
  if not name:
    all_goods = STATE.goods.get(ctx, {})
    if not all_goods:
      await show_goods.finish("目前没有商品")
    segments = ["所有商品："]
    for id, goods in all_goods.items():
      if goods.disabled:
        price = "已下架"
      else:
        price = f"{goods.price}金币"
      segments.append(f"{id:09} - {goods.name}: {price}")
    await show_goods.finish("\n".join(segments))
  else:
    try:
      id, goods = find_goods(ctx, name)
    except helper.AggregateError as e:
      await show_goods.finish("\n".join(e))
    await show_goods.finish(await format_goods(bot, event, id, goods))

purchase = (command.CommandBuilder("purchase.purchase", "购买")
  .in_group()
  .brief("购买金币商品")
  .usage("/购买商品 <名字或ID> - 购买指定商品，购买后会提醒商品的所有人")
  .build())
@purchase.handle()
async def handle_purchase(bot: Bot, event: MessageEvent, state: T_State, arg: Message = CommandArg()):
  name = arg.extract_plain_text().rstrip()
  ctx = context.get_event_context(event)
  try:
    id, goods = find_goods(ctx, name)
  except helper.AggregateError as e:
    await purchase.finish("\n".join(e))
  state["id"] = id
  formatted = await format_goods(bot, event, id, goods)
  if goods.disabled:
    await purchase.finish(formatted + "\n商品已下架，无法购买")
  if goods.total != 0 and goods.total_purchased >= goods.total:
    await purchase.finish(formatted + "\n商品已售罄，无法购买")
  if goods.single != 0 and goods.single_purchased.get(event.user_id, 0) >= goods.single:
    await purchase.finish(formatted + f"\n你已经买了 {goods.single} 份该商品，无法购买")
  balance = currency.get_coin(ctx, event.user_id)
  new_balance = balance - goods.price
  if new_balance < 0:
    await purchase.finish(formatted + f"\n余额：{balance}\n余额不足，无法购买")
  await purchase.send(formatted + f"\n余额：{balance} → {new_balance}\n发送“确定”确定购买，发送“取消”或其他消息取消购买")

@purchase.got("choice")
async def got_purchase(bot: Bot, event: MessageEvent, state: T_State, choice: str = ArgPlainText()):
  if choice.strip() != "确定":
    await purchase.finish("购买已取消")
  ctx = context.get_event_context(event)
  goods = STATE.goods[ctx][state["id"]]
  if goods.disabled:
    await purchase.finish("商品已下架，无法购买")
  if goods.total != 0 and goods.total_purchased >= goods.total:
    await purchase.finish("商品已售罄，无法购买")
  if goods.single != 0 and goods.single_purchased.get(event.user_id, 0) >= goods.single:
    await purchase.finish(f"\n你已经买了 {goods.single} 份该商品，无法购买")
  balance = currency.get_coin(ctx, event.user_id)
  if balance < goods.price:
    await purchase.finish("余额不足，无法购买")
  currency.add_coin(ctx, event.user_id, -goods.price)
  goods.total_purchased += 1
  if event.user_id in goods.single_purchased:
    goods.single_purchased[event.user_id] += 1
  else:
    goods.single_purchased[event.user_id] = 1
  STATE.dump()
  if ctx == getattr(event, "group_id", -1):
    await purchase.finish(f"你已成功购买该商品，请与商品的主人沟通：" + MessageSegment.at(goods.notify))
  else:
    info = await bot.get_group_member_info(group_id=ctx, user_id=event.user_id)
    username = info["card"] or info["nickname"]
    await bot.send_group_msg(group_id=ctx, message=MessageSegment.at(goods.notify) + f"{username}（{event.user_id}）购买了你的商品 {goods.name}，请注意！")
    await purchase.finish(f"你已成功购买该商品，请与商品的主人沟通")
