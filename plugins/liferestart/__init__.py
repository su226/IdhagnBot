import html
import itertools
import random
from argparse import Namespace
from typing import Awaitable, Callable, Dict, Iterable, List, Optional, Set, Tuple, Union, cast

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image
from pydantic import BaseModel, Field

from util import command, configs, context, imutil, misc, textutil

from .game import Config as GameConfig, Game, GeneratedCharacter, Statistics
from .game.config import StatRarityItem
from .game.data import ACHIEVEMENT, CHARACTER, EVENT, TALENT
from .game.struct.character import Character
from .game.struct.commons import Rarity
from .game.struct.talent import Talent


class Config(BaseModel):
  game: GameConfig = Field(default_factory=GameConfig)
  progress_group_by: int = 50
  character_group_by: int = 25


class State(BaseModel):
  statistics: Dict[int, Statistics] = Field(default_factory=dict)

  def get_statistics(self, id: int) -> Statistics:
    if id not in self.statistics:
      self.statistics[id] = Statistics()
    return self.statistics[id]


CONFIG = configs.SharedConfig("liferestart", Config)
STATE = configs.SharedState("liferestart", State)


def find_character(name: str) -> Optional[Character]:
  for i in CHARACTER.values():
    if i.name == name:
      return i
  for i in STATE().statistics.values():
    if i.character and i.character.name == name:
      return i.character
  return None


def random_alloc(game: Game, total: int) -> List[int]:
  result = [game.config.stat.min] * 4
  for _ in range(total):
    result[random.choice([i for i, v in enumerate(result) if v < game.config.stat.max])] += 1
  return result


RARITY_COLOR = {
  Rarity.COMMON: "ffffff",
  Rarity.UNCOMMON: "82b1ff",
  Rarity.RARE: "ea80fc",
  Rarity.LEGENDARY: "ffd180",
}


def make_image(messages: Iterable[Union[Tuple[Rarity, str], str]]) -> MessageSegment:
  lines = []
  for line in messages:
    if isinstance(line, tuple):
      rarity, content = line
    else:
      rarity = Rarity.COMMON
      content = line
    lines.append(f"<span color=\"#{RARITY_COLOR[rarity]}\">{html.escape(content)}</span>")
  text_im = textutil.render(
    "\n".join(lines), "sans", 32, box=576, color=(255, 255, 255), markup=True
  )
  im = Image.new("RGB", (text_im.width + 64, text_im.height + 64), (38, 50, 56))
  im.paste(text_im, (32, 32), text_im)
  return imutil.to_segment(im)


def format_float(value: float) -> str:
  # 处理唯一一个属性有浮点数的角色祖冲之
  return f"{value:.7f}".rstrip(".0") or "0"


def get_messages(game: Game) -> List[str]:
  messages = []
  prev_charm = -1
  prev_intelligence = -1
  prev_strength = -1
  prev_money = -1
  prev_spirit = -1
  for progress in game.progress():
    segments = []
    if (
      progress.charm != prev_charm or progress.intelligence != prev_intelligence
      or progress.strength != prev_strength or progress.money != prev_money
      or progress.spirit != prev_spirit
    ):
      segments.append((
        Rarity.COMMON,
        f"颜值 {format_float(progress.charm)} 智力 {format_float(progress.intelligence)} "
        f"体质 {format_float(progress.strength)}  家境 {format_float(progress.money)} "
        f"快乐 {progress.spirit}"
      ))
    prev_charm = progress.charm
    prev_intelligence = progress.intelligence
    prev_strength = progress.strength
    prev_money = progress.money
    prev_spirit = progress.spirit
    for talent in progress.talents:
      segments.append((talent.rarity, f"天赋 {talent.name} 发动: {talent.description}"))
    for game_event, has_next in progress.events:
      segments.append((game_event.rarity, game_event.event))
      if not has_next and game_event.post:
        segments.append((game_event.rarity, game_event.post))
    for achievement in progress.achievements:
      segments.append((
        achievement.rarity, f"获得成就 {achievement.name}: {achievement.description}"
      ))
    age = "出生" if progress.age == -1 else f"{progress.age}岁"
    segments[0] = (segments[0][0], f"{age} - {segments[0][1]}")
    messages.append(segments)

  end = game.end()
  segments = [
    "---- 总结 ----",
    (
      end.summary_charm.rarity,
      f"颜值: {format_float(end.charm)} - "
      + game.config.stat.rarity.messages[end.summary_charm.message_id]
    ),
    (
      end.summary_intelligence.rarity,
      f"智力: {format_float(end.intelligence)} - "
      + game.config.stat.rarity.messages[end.summary_intelligence.message_id]
    ),
    (
      end.summary_strength.rarity,
      f"体质: {format_float(end.strength)} - "
      + game.config.stat.rarity.messages[end.summary_strength.message_id]
    ),
    (
      end.summary_money.rarity,
      f"家境: {format_float(end.money)} - "
      + game.config.stat.rarity.messages[end.summary_money.message_id]
    ),
    (
      end.summary_spirit.rarity,
      f"快乐: {end.spirit} - "
      + game.config.stat.rarity.messages[end.summary_spirit.message_id]
    ),
    (
      end.summary_age.rarity,
      f"享年: {end.age} - "
      + game.config.stat.rarity.messages[end.summary_age.message_id]
    ),
    (
      end.summary_overall.rarity,
      f"总评: {end.overall} - "
      + game.config.stat.rarity.messages[end.summary_overall.message_id]
    ),
  ]
  for achievement in end.achievements:
    segments.append(
      (achievement.rarity, f"获得成就 {achievement.name}: {achievement.description}")
    )
  messages.append(segments)
  return messages

parser = ArgumentParser(add_help=False)
subparsers = parser.add_subparsers(required=True)

async def handle_classic(bot: Bot, event: MessageEvent, args: Namespace) -> None:
  game = Game(CONFIG().game, STATE().get_statistics(event.user_id))
  seed = game.seed(args.seed)
  seed_shown = False

  inherited = (
    None if game.statistics.inherited_talent == -1 else TALENT[game.statistics.inherited_talent])
  talents: List[Talent] = []
  for choices in game.random_talents():
    segments: List[str] = []
    if not seed_shown:
      segments.append(f"种子：{seed}")
      seed_shown = True
    min_choice = 1
    if inherited:
      min_choice = 0
      segments.append(f"0: {inherited.name} - {inherited.description}")
    for i, talent in enumerate(choices, 1):
      segments.append(f"{i}: {talent.name} - {talent.description}")
    segments.append(
      f"- 发送 {game.config.talent.limit} 个空格分隔的数字选择天赋，第一个天赋将会被继承")
    segments.append("- 发送 “随” 随机选择")
    segments.append("- 发送 “换” 重新抽天赋")
    segments.append("- 发送 “退” 退出游戏")
    await liferestart.send("\n".join(segments))
    choice = ""
    while True:
      try:
        msg = await misc.prompt(event)
      except misc.PromptTimeout:
        await liferestart.finish("等待回应超时，已退出游戏")
      choice = msg.extract_plain_text()
      if choice in ("退", "换", "随"):
        break
      try:
        selected = [int(i) for i in choice.split()]
      except ValueError:
        await liferestart.send("只能输入数字")
        continue
      if any(i < min_choice or i > len(choices) for i in selected):
        await liferestart.send(f"只能输入 {min_choice} 和 {len(choices)} 之间的数字")
        continue
      if len(selected) > 0 and len(selected) != game.config.talent.limit:
        await liferestart.send(f"只能选择恰好 {game.config.talent.limit} 个天赋")
        continue
      talents = [cast(Talent, inherited) if i == 0 else choices[i - 1] for i in selected]
      talent_errors: Set[str] = set()
      for i, j in itertools.combinations(talents, 2):
        if i.is_imcompatible_with(j):
          talent_errors.add(f"不能同时选择 {i.name} 和 {j.name}")
        elif i is j:
          talent_errors.add("每个天赋只能选择一次")
      if talent_errors:
        await liferestart.send("\n".join(talent_errors))
        continue
      break
    if choice == "退":
      await liferestart.finish("已退出游戏")
    elif choice == "换":
      continue
    elif choice == "随":
      talents = []
      for _ in range(game.config.talent.limit):
        while True:
          selected = random.randint(min_choice, game.config.talent.limit)
          talent = cast(Talent, inherited) if selected == 0 else choices[selected - 1]
          if not any(talent == x or talent.is_imcompatible_with(x) for x in talents):
            talents.append(talent)
            break
    break
  real_talents = game.set_talents(talents)

  segments = ["已选天赋:"]
  for talent, real in zip(talents, real_talents):
    segments.append(f"{talent.name} - {talent.description}")
    if talent is not real:
      segments.append(f"-> {real.name} - {real.description}")
  points = game.get_points()
  segments.append(f"可分配 {points} 点属性")
  segments.append("- 发送 4 个空格分隔的数字分配颜值、智力、体质和家境")
  segments.append("- 发送 “随” 随机分配")
  segments.append("- 发送 “退” 退出游戏")
  await liferestart.send("\n".join(segments))
  stats: List[int] = []
  choice = ""
  while True:
    try:
      msg = await misc.prompt(event)
    except misc.PromptTimeout:
      await liferestart.finish("等待回应超时，已退出游戏")
    choice = msg.extract_plain_text()
    if choice in ("退", "随"):
      break
    try:
      stats = [int(i) for i in choice.split()]
    except ValueError:
      await liferestart.send("只能输入数字")
      continue
    if len(stats) != 4:
      await liferestart.send("请输入恰好 4 个数字")
      continue
    if any(x < game.config.stat.min or x > game.config.stat.max for x in stats):
      await liferestart.send(f"属性必须在 {game.config.stat.min} 和 {game.config.stat.max} 之间")
      continue
    if sum(stats) != points:
      await liferestart.send(f"必须刚好分配完 {points} 点属性")
      continue
    break
  if choice == "退":
    await liferestart.finish("已退出游戏")
  elif choice == "随":
    stats = random_alloc(game, points)
  game.set_stats(*stats)

  messages = get_messages(game)
  game.statistics.inherited_talent = talents[0].id
  STATE.dump()

  for part in misc.chunked(messages, CONFIG().progress_group_by):
    await liferestart.send(await misc.to_thread(
      make_image, itertools.chain.from_iterable(part)
    ))

classic = subparsers.add_parser("经典", aliases=["c"], help="游玩经典模式")
classic.add_argument("--seed", "-s", nargs="?", type=int, metavar="种子")
classic.set_defaults(func=handle_classic)

def get_character_segments(ch: Character) -> List[str]:
  segments = [f"---- {ch.name} ----"]
  if isinstance(ch, GeneratedCharacter) and ch.seed != -1:
    segments.append(f"种子：{ch.seed}")
  segments.append(
    f"颜值 {format_float(ch.charm)} 智力 {format_float(ch.intelligence)} "
    f"体质 {format_float(ch.strength)} 家境 {format_float(ch.money)}"
  )
  for i in ch.talents:
    ta = TALENT[i]
    segments.append(f"{ta.name} - {ta.description}")
  return segments

async def handle_character_view(bot: Bot, event: MessageEvent, args: Namespace) -> None:
  if args.name:
    ch = find_character(args.name)
    if ch is None:
      await liferestart.finish("没有这个角色")
  else:
    st = STATE().statistics.get(event.user_id, None)
    if st is None or st.character is None:
      await liferestart.finish("你还没有自定义角色")
    ch = st.character
  await liferestart.send("\n".join(get_character_segments(ch)))

character_view = subparsers.add_parser("查看角色", help="查看自己或别人的角色")
character_view.add_argument("name", nargs="?", metavar="名字")
character_view.set_defaults(func=handle_character_view)

async def handle_character_list(bot: Bot, event: MessageEvent, args: Namespace) -> None:
  messages = [["==== 前世名人 ====", ""]]
  for ch in CHARACTER.values():
    messages.append(get_character_segments(ch))
  custom_messages = []
  for i in STATE().statistics.values():
    if ch := i.character:
      custom_messages.append(get_character_segments(ch))
  if custom_messages:
    messages.append(["", "---- 自定义角色 ----", ""])
    messages.extend(custom_messages)
  for part in misc.chunked(messages, CONFIG().character_group_by):
    await liferestart.send(await misc.to_thread(
      make_image, itertools.chain.from_iterable(part)
    ))

character_list = subparsers.add_parser("角色列表", help="列出别人的角色")
character_list.set_defaults(func=handle_character_list)

async def handle_character_create(bot: Bot, event: MessageEvent, args: Namespace) -> None:
  await liferestart.send(
    "一旦创建角色将不能修改或删除，但可重命名，名字中不能有空格"
    "\n- 发送“退”取消\n- 发送名字创建角色"
  )
  try:
    msg = await misc.prompt(event)
  except misc.PromptTimeout:
    await liferestart.finish("等待回应超时，已退出游戏")
  name = msg.extract_plain_text().strip()
  if name == "退":
    await liferestart.finish("创建取消")
  elif " " in name:
    await liferestart.finish("创建失败：名字中不能有空格")
  elif find_character(name):
    await liferestart.finish("创建失败：已有这个名字的角色")
  game = Game(CONFIG().game, STATE().get_statistics(event.user_id))
  character = game.create_character()
  STATE.dump()
  await liferestart.finish(f"已创建角色，种子为：{character.seed}")

character_create = subparsers.add_parser("创建角色", help="创建自己的角色")
character_create.set_defaults(func=handle_character_create)

async def handle_character_rename(bot: Bot, event: MessageEvent, args: Namespace) -> None:
  state = STATE()
  st = state.statistics.get(event.user_id, None)
  if st is None or st.character is None:
    await liferestart.finish("你还没有自定义角色")
  elif args.name == st.character.name:
    await liferestart.finish(f"你的角色已经叫 {args.name} 了")
  elif find_character(args.name):
    await liferestart.finish(f"已经有叫 {args.name} 的角色了")
  st.character.name = args.name
  STATE.dump()
  await liferestart.finish(f"你的角色已重命名为 {args.name}")

character_rename = subparsers.add_parser("重命名角色", help="重命名自己的角色")
character_rename.add_argument("name", nargs="?", metavar="名字")
character_rename.set_defaults(func=handle_character_rename)

async def handle_character_play(bot: Bot, event: MessageEvent, args: Namespace) -> None:
  config = CONFIG()
  state = STATE()
  if args.name:
    ch = find_character(args.name)
    if ch is None:
      await liferestart.finish("没有这个角色")
  else:
    st = state.statistics.get(event.user_id, None)
    if st is None or st.character is None:
      await liferestart.finish("你还没有自定义角色")
    ch = st.character
  game = Game(config.game, state.get_statistics(event.user_id))
  seed = game.seed(args.seed)
  talents, real_talents = game.set_character(ch)

  segments = [f"---- {ch.name} ----"]
  segments.append(f"游戏种子：{seed}")
  if isinstance(ch, GeneratedCharacter) and ch.seed != -1:
    segments.append(f"角色种子：{ch.seed}")
  segments.append(
    f"颜值 {format_float(ch.charm)} 智力 {format_float(ch.intelligence)} "
    f"体质 {format_float(ch.strength)} 家境 {format_float(ch.money)}"
  )
  for talent, real in zip(talents, real_talents):
    segments.append(f"{talent.name} - {talent.description}")
    if talent is not real:
      segments.append(f"-> {real.name} - {real.description}")
  await liferestart.send("\n".join(segments))

  messages = get_messages(game)
  STATE.dump()
  for part in misc.chunked(messages, config.progress_group_by):
    await liferestart.send(await misc.to_thread(
      make_image, itertools.chain.from_iterable(part)
    ))

character_play = subparsers.add_parser("角色", aliases=["h"], help="游玩名人或自定义角色")
character_play.add_argument("name", nargs="?", metavar="名字")
character_play.add_argument("--seed", "-s", nargs="?", type=int, metavar="种子")
character_play.set_defaults(func=handle_character_play)

async def handle_achievements(bot: Bot, event: MessageEvent, args: Namespace) -> None:
  st = STATE().statistics.get(event.user_id, None)
  if st is None:
    await liferestart.finish("你还没重开过")
  game = Game(CONFIG().game, st)
  finished_games = game.judge(st.finished_games, game.config.stat.rarity.finished_games)
  achievements = game.judge(len(st.achievements), game.config.stat.rarity.achievements)
  events_value = int(len(st.events) / len(EVENT) * 100)
  events = game.judge(events_value, game.config.stat.rarity.event_percentage)
  talents_value = int(len(st.talents) / len(TALENT) * 100)
  talents = game.judge(talents_value, game.config.stat.rarity.talent_percentage)
  segments = [
    "---- 成就与统计 ----",
    (
      finished_games.rarity,
      f"重开次数: {st.finished_games:3} - "
      + game.config.stat.rarity.messages[finished_games.message_id]
    ),
    (
      achievements.rarity,
      f"成就数量: {len(st.achievements):3} - "
      + game.config.stat.rarity.messages[achievements.message_id]
    ),
    (events.rarity, f"事件收集率: {events_value:3}%"),
    (talents.rarity, f"天赋游玩率: {talents_value:3}%"),
  ]
  for achievement in ACHIEVEMENT.values():
    granted = achievement.id in st.achievements
    hidden = achievement.hidden and not granted
    symbol = "✓" if granted else "×"
    name = "???" if hidden else achievement.name
    description = "隐藏成就" if hidden else achievement.description
    segments.append((achievement.rarity, f"{symbol} {name} - {description}"))
  await liferestart.send(await misc.to_thread(make_image, segments))

achievements = subparsers.add_parser("成就", help="查看成就和统计")
achievements.set_defaults(func=handle_achievements)

def leaderboard_factory(
  getter: Callable[[Statistics], int],
  rarities: Callable[[], List[StatRarityItem]], suffix: str = ""
) -> Callable[[Bot, MessageEvent, Namespace], Awaitable[None]]:
  async def handler(bot: Bot, event: MessageEvent, args: Namespace) -> None:
    state = STATE()
    leaderboard = [(id, getter(st)) for id, st in state.statistics.items()]
    leaderboard.sort(key=lambda x: x[1], reverse=True)
    segments = []
    ctx = context.get_event_context(event)
    if ctx == -1:
      members: Dict[int, str] = {}
    else:
      members = {
        i["user_id"]: i["card"] or i["nickname"]
        for i in await bot.get_group_member_list(group_id=ctx)
      }
    for id, v in leaderboard:
      judge = Game.judge(v, rarities())
      if id in members:
        name = members[id]
      else:
        name = (await bot.get_stranger_info(user_id=id))["nickname"]
      segments.append((judge.rarity, f"{name} - {v}{suffix}"))
    await liferestart.send(await misc.to_thread(make_image, segments))
  return handler

finished_leaderboard = subparsers.add_parser("重开排行", help="查看重开次数排行")
finished_leaderboard.set_defaults(func=leaderboard_factory(
  lambda x: x.finished_games, lambda: CONFIG().game.stat.rarity.finished_games
))
achievements_leaderboard = subparsers.add_parser("成就排行", help="查看成就数排行")
achievements_leaderboard.set_defaults(func=leaderboard_factory(
  lambda x: len(x.achievements), lambda: CONFIG().game.stat.rarity.achievements
))
events_leaderboard = subparsers.add_parser("事件排行", help="查看天赋游玩率排行")
events_leaderboard.set_defaults(func=leaderboard_factory(
  lambda x: int(len(x.events) / len(EVENT) * 100),
  lambda: CONFIG().game.stat.rarity.event_percentage, "%"
))
talents_leaderboard = subparsers.add_parser("天赋排行", help="查看事件收集率排行")
talents_leaderboard.set_defaults(func=leaderboard_factory(
  lambda x: int(len(x.talents) / len(TALENT) * 100),
  lambda: CONFIG().game.stat.rarity.talent_percentage, "%"
))

liferestart = (
  command.CommandBuilder(
    "liferestart", "人生重开", "liferestart", "life", "restart", "remake", "人生", "重开")
  .brief("现可在群里快速重开")
  .shell(parser)
  .build()
)
@liferestart.handle()
async def handle_liferestart(
  bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()
) -> None:
  await args.func(bot, event, args)
