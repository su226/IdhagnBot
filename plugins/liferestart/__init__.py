import asyncio
import itertools
import random
from argparse import Namespace
from io import BytesIO
from typing import AsyncGenerator, Callable, Generator, Iterable, TypeVar, cast

import nonebot
from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent, MessageSegment
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageDraw, ImageFont
from pydantic import Field

from util import command, context, resources
from util.config import BaseConfig, BaseState

from .game import Config as GameConfig
from .game import Game, GeneratedCharacter, Statistics
from .game.config import StatRarityItem
from .game.data import ACHIEVEMENT, CHARACTER, EVENT, TALENT
from .game.struct.character import Character
from .game.struct.commons import Rarity
from .game.struct.talent import Talent


class Config(BaseConfig):
  __file__ = "liferestart"
  game: GameConfig = Field(default_factory=GameConfig)
  progress_group_by: int = 50
  character_group_by: int = 25


class State(BaseState):
  __file__ = "liferestart"
  statistics: dict[int, Statistics] = Field(default_factory=dict)

  def get_statistics(self, id: int) -> Statistics:
    if id not in self.statistics:
      self.statistics[id] = Statistics()
    return self.statistics[id]


CONFIG = Config.load()
STATE = State.load()


async def prompt(event: MessageEvent) -> AsyncGenerator[Message, None]:
  async def check_prompt(event2: MessageEvent):
    return (
      event.user_id == event2.user_id
      and getattr(event, "group_id", -1) == getattr(event2, "group_id", -1))

  async def handle_prompt(event2: MessageEvent):
    future.set_result(event2.get_message())
  while True:
    future = asyncio.get_event_loop().create_future()
    nonebot.on_message(check_prompt, handlers=[handle_prompt], temp=True, priority=-1)
    yield await future


def find_character(name: str) -> Character | None:
  for i in CHARACTER.values():
    if i.name == name:
      return i
  for i in STATE.statistics.values():
    if i.character and i.character.name == name:
      return i.character
  return None


def random_alloc(game: Game, total: int) -> list[int]:
  result = [game.config.stat.min] * 4
  for _ in range(total):
    result[random.choice([i for i, v in enumerate(result) if v < game.config.stat.max])] += 1
  return result


TItem = TypeVar("TItem")


def groupbyn(iterable: Iterable[TItem], n: int) -> Generator[list[TItem], None, None]:
  result: list[TItem] = []
  for i in iterable:
    result.append(i)
    if len(result) == n:
      yield result
      result.clear()
  if result:
    yield result


WIDTH = 576


def wrap(font: ImageFont.FreeTypeFont, text: str) -> Generator[str, None, None]:
  cur = []
  curwidth = 0
  for ch in text:
    chwidth, _ = font.getsize(ch)
    if curwidth + chwidth > WIDTH:
      yield "".join(cur)
      cur.clear()
      curwidth = 0
    cur.append(ch)
    curwidth += chwidth
  if cur:
    yield "".join(cur)


RARITY_COLOR = {
  Rarity.COMMON: (255, 255, 255),
  Rarity.UNCOMMON: (130, 177, 255),
  Rarity.RARE: (234, 128, 252),
  Rarity.LEGENDARY: (255, 209, 128),
}


def make_image(
  font: ImageFont.FreeTypeFont, messages: Iterable[tuple[Rarity, str] | str]
) -> Image.Image:
  line_height = font.getsize("A")[1] + 4
  lines = []
  for line in messages:
    if isinstance(line, tuple):
      rarity, text = line
    else:
      rarity = Rarity.COMMON
      text = line
    lines.extend((rarity, i) for i in wrap(font, text))
  im = Image.new("RGB", (640, line_height * len(lines) + 32 + font.getmetrics()[1]), (38, 50, 56))
  draw = ImageDraw.Draw(im)
  for i, (rarity, text) in enumerate(lines):
    draw.text((16, 16 + i * line_height), text, RARITY_COLOR[rarity], font)
  f = BytesIO()
  im.save(f, "jpeg")
  return im


def get_messages(game: Game) -> list[str]:
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
        Rarity.COMMON, f"?????? {progress.charm} ?????? {progress.intelligence}"
        f"?????? {progress.strength} ?????? {progress.money} ?????? {progress.spirit}"))
    prev_charm = progress.charm
    prev_intelligence = progress.intelligence
    prev_strength = progress.strength
    prev_money = progress.money
    prev_spirit = progress.spirit
    for talent in progress.talents:
      segments.append((talent.rarity, f"?????? {talent.name} ??????: {talent.description}"))
    for game_event, has_next in progress.events:
      segments.append((game_event.rarity, game_event.event))
      if not has_next and game_event.post:
        segments.append((game_event.rarity, game_event.post))
    for achievement in progress.achievements:
      segments.append((
        achievement.rarity, f"???????????? {achievement.name}: {achievement.description}"))
    age = "??????" if progress.age == -1 else f"{progress.age}???"
    segments[0] = (segments[0][0], f"{age} - {segments[0][1]}")
    messages.append(segments)

  end = game.end()
  segments = [
    "---- ?????? ----",
    (end.summary_charm.rarity,
      f"??????: {end.charm} - {game.config.stat.rarity.messages[end.summary_charm.message_id]}"),
    (end.summary_intelligence.rarity,
      f"??????: {end.intelligence} - "
      + game.config.stat.rarity.messages[end.summary_intelligence.message_id]),
    (end.summary_strength.rarity,
      f"??????: {end.strength} - "
      + game.config.stat.rarity.messages[end.summary_strength.message_id]),
    (end.summary_money.rarity,
      f"??????: {end.money} - {game.config.stat.rarity.messages[end.summary_money.message_id]}"),
    (end.summary_spirit.rarity,
      f"??????: {end.spirit} - {game.config.stat.rarity.messages[end.summary_spirit.message_id]}"),
    (end.summary_age.rarity,
      f"??????: {end.age} - {game.config.stat.rarity.messages[end.summary_age.message_id]}"),
    (end.summary_overall.rarity,
      f"??????: {end.overall} - {game.config.stat.rarity.messages[end.summary_overall.message_id]}"),
  ]
  for achievement in end.achievements:
    segments.append((achievement.rarity, f"???????????? {achievement.name}: {achievement.description}"))
  messages.append(segments)
  return messages


parser = ArgumentParser(add_help=False)
subparsers = parser.add_subparsers(required=True)


async def handle_classic(bot: Bot, event: MessageEvent, args: Namespace):
  game = Game(CONFIG.game, STATE.get_statistics(event.user_id))
  seed = game.seed(args.seed)
  seed_shown = False

  inherited = (
    None if game.statistics.inherited_talent == -1 else TALENT[game.statistics.inherited_talent])
  talents: list[Talent] = []
  for choices in game.random_talents():
    segments: list[str] = []
    if not seed_shown:
      segments.append(f"?????????{seed}")
      seed_shown = True
    min_choice = 1
    if inherited:
      min_choice = 0
      segments.append(f"0: {inherited.name} - {inherited.description}")
    for i, talent in enumerate(choices, 1):
      segments.append(f"{i}: {talent.name} - {talent.description}")
    segments.append(
      f"- ?????? {game.config.talent.limit} ?????????????????????????????????????????????????????????????????????")
    segments.append("- ?????? ????????? ????????????")
    segments.append("- ?????? ????????? ???????????????")
    segments.append("- ?????? ????????? ????????????")
    await liferestart.send("\n".join(segments))
    choice = ""
    async for message in prompt(event):
      choice = message.extract_plain_text()
      if choice in ("???", "???", "???"):
        break
      try:
        selected = [int(i) for i in choice.split()]
      except ValueError:
        await liferestart.send("??????????????????")
        continue
      if any(i < min_choice or i > len(choices) for i in selected):
        await liferestart.send(f"???????????? {min_choice} ??? {len(choices)} ???????????????")
        continue
      if len(selected) > 0 and len(selected) != game.config.talent.limit:
        await liferestart.send(f"?????????????????? {game.config.talent.limit} ?????????")
        continue
      talents = [cast(Talent, inherited) if i == 0 else choices[i - 1] for i in selected]
      for i, j in itertools.combinations(talents, 2):
        if i.is_imcompatible_with(j):
          await liferestart.send(f"?????????????????? {i.name} ??? {j.name}")
          continue
        elif i is j:
          await liferestart.send("??????????????????????????????")
          continue
      break
    if choice == "???":
      await liferestart.finish("???????????????")
    elif choice == "???":
      continue
    elif choice == "???":
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

  segments = ["????????????:"]
  for talent, real in zip(talents, real_talents):
    segments.append(f"{talent.name} - {talent.description}")
    if talent is not real:
      segments.append(f"-> {real.name} - {real.description}")
  points = game.get_points()
  segments.append(f"????????? {points} ?????????")
  segments.append("- ?????? 4 ???????????????????????????????????????????????????????????????")
  segments.append("- ?????? ????????? ????????????")
  segments.append("- ?????? ????????? ????????????")
  await liferestart.send("\n".join(segments))
  stats: list[int] = []
  choice = ""
  async for msg in prompt(event):
    choice: str = str(msg)
    if choice in ("???", "???"):
      break
    try:
      stats = [int(i) for i in choice.split()]
    except ValueError:
      await liferestart.send("??????????????????")
      continue
    if len(stats) != 4:
      await liferestart.send("??????????????? 4 ?????????")
      continue
    if any(x < game.config.stat.min or x > game.config.stat.max for x in stats):
      await liferestart.send(f"??????????????? {game.config.stat.min} ??? {game.config.stat.max} ??????")
      continue
    if sum(stats) != points:
      await liferestart.send(f"????????????????????? {points} ?????????")
      continue
    break
  if choice == "???":
    await liferestart.finish("???????????????")
  elif choice == "???":
    stats = random_alloc(game, points)
  game.set_stats(*stats)

  messages = get_messages(game)
  game.statistics.inherited_talent = talents[0].id
  STATE.dump()

  font = resources.font("sans", 32)
  for part in groupbyn(messages, CONFIG.progress_group_by):
    f = BytesIO()
    make_image(font, itertools.chain.from_iterable(part)).save(f, "png")
    await liferestart.send(MessageSegment.image(f))

classic = subparsers.add_parser("??????", aliases=["c"], help="??????????????????")
classic.add_argument("-seed", "-??????", nargs="?", type=int, metavar="??????")
classic.set_defaults(func=handle_classic)


def get_character_segments(ch: Character) -> list[str]:
  segments = [f"---- {ch.name} ----"]
  if isinstance(ch, GeneratedCharacter) and ch.seed != -1:
    segments.append(f"?????????{ch.seed}")
  segments.append(f"?????? {ch.charm} ?????? {ch.intelligence} ?????? {ch.strength} ?????? {ch.money}")
  for i in ch.talents:
    ta = TALENT[i]
    segments.append(f"{ta.name} - {ta.description}")
  return segments


async def handle_character_view(bot: Bot, event: MessageEvent, args: Namespace):
  if args.name:
    ch = find_character(args.name)
    if ch is None:
      await liferestart.finish("??????????????????")
  else:
    st = STATE.statistics.get(event.user_id, None)
    if st is None or st.character is None:
      await liferestart.finish("???????????????????????????")
    ch = st.character
  await liferestart.send("\n".join(get_character_segments(ch)))

character_view = subparsers.add_parser("????????????", help="??????????????????????????????")
character_view.add_argument("name", nargs="?", metavar="??????")
character_view.set_defaults(func=handle_character_view)


async def handle_character_list(bot: Bot, event: MessageEvent, args: Namespace):
  messages = [["---- ???????????? ----", ""]]
  for ch in CHARACTER.values():
    messages.append(get_character_segments(ch))
  messages.append(["", "---- ??????????????? ----", ""])
  for i in STATE.statistics.values():
    if ch := i.character:
      messages.append(get_character_segments(ch))
  font = resources.font("sans", 32)
  for part in groupbyn(messages, CONFIG.character_group_by):
    f = BytesIO()
    make_image(font, itertools.chain.from_iterable(part)).save(f, "png")
    await liferestart.send(MessageSegment.image(f))

character_list = subparsers.add_parser("????????????", help="?????????????????????")
character_list.set_defaults(func=handle_character_list)


async def handle_character_create(bot: Bot, event: MessageEvent, args: Namespace):
  await liferestart.send(
    "???????????????????????????????????????????????????????????????????????????????????????"
    "\n- ?????????????????????\n- ????????????????????????")
  name = ""
  async for msg in prompt(event):
    name = msg.extract_plain_text()
    break
  if name == "???":
    await liferestart.finish("????????????")
  elif " " in name:
    await liferestart.finish("???????????????????????????????????????")
  elif find_character(name):
    await liferestart.finish("??????????????????????????????????????????")
  game = Game(CONFIG.game, STATE.get_statistics(event.user_id))
  character = game.create_character()
  STATE.dump()
  await liferestart.finish(f"??????????????????????????????{character.seed}")

character_create = subparsers.add_parser("????????????", help="?????????????????????")
character_create.set_defaults(func=handle_character_create)


async def handle_character_rename(bot: Bot, event: MessageEvent, args: Namespace):
  st = STATE.statistics.get(event.user_id, None)
  if st is None or st.character is None:
    await liferestart.finish("???????????????????????????")
  elif args.name == st.character.name:
    await liferestart.finish(f"????????????????????? {args.name} ???")
  elif find_character(args.name):
    await liferestart.finish(f"???????????? {args.name} ????????????")
  st.character.name = args.name
  STATE.dump()
  await liferestart.finish(f"??????????????????????????? {args.name}")

character_rename = subparsers.add_parser("???????????????", help="????????????????????????")
character_rename.add_argument("name", nargs="?", metavar="??????")
character_rename.set_defaults(func=handle_character_rename)


async def handle_character_play(bot: Bot, event: MessageEvent, args: Namespace):
  if args.name:
    ch = find_character(args.name)
    if ch is None:
      await liferestart.finish("??????????????????")
  else:
    st = STATE.statistics.get(event.user_id, None)
    if st is None or st.character is None:
      await liferestart.finish("???????????????????????????")
    ch = st.character
  game = Game(CONFIG.game, STATE.get_statistics(event.user_id))
  seed = game.seed(args.seed)
  talents, real_talents = game.set_character(ch)

  segments = [f"---- {ch.name} ----"]
  segments.append(f"???????????????{seed}")
  if isinstance(ch, GeneratedCharacter) and ch.seed != -1:
    segments.append(f"???????????????{ch.seed}")
  segments.append(f"?????? {ch.charm} ?????? {ch.intelligence} ?????? {ch.strength} ?????? {ch.money}")
  for talent, real in zip(talents, real_talents):
    segments.append(f"{talent.name} - {talent.description}")
    if talent is not real:
      segments.append(f"-> {real.name} - {real.description}")
  await liferestart.send("\n".join(segments))

  messages = get_messages(game)
  STATE.dump()
  font = resources.font("sans", 32)
  for part in groupbyn(messages, CONFIG.progress_group_by):
    f = BytesIO()
    make_image(font, itertools.chain.from_iterable(part)).save(f, "png")
    await liferestart.send(MessageSegment.image(f))

character_play = subparsers.add_parser("??????", aliases=["h"], help="??????????????????????????????")
character_play.add_argument("name", nargs="?", metavar="??????")
character_play.add_argument("-seed", "-??????", nargs="?", type=int, metavar="??????")
character_play.set_defaults(func=handle_character_play)


async def handle_achievements(bot: Bot, event: MessageEvent, args: Namespace):
  st = STATE.statistics.get(event.user_id, None)
  if st is None:
    await liferestart.finish("??????????????????")
  game = Game(CONFIG.game, st)
  finished_games = game.judge(st.finished_games, game.config.stat.rarity.finished_games)
  achievements = game.judge(len(st.achievements), game.config.stat.rarity.achievements)
  events_value = int(len(st.events) / len(EVENT) * 100)
  events = game.judge(events_value, game.config.stat.rarity.event_percentage)
  talents_value = int(len(st.talents) / len(TALENT) * 100)
  talents = game.judge(talents_value, game.config.stat.rarity.talent_percentage)
  segments = [
    "---- ??????????????? ----",
    (finished_games.rarity, f"????????????: {st.finished_games:3} - "
      + game.config.stat.rarity.messages[finished_games.message_id]),
    (achievements.rarity, f"????????????: {len(st.achievements):3} - "
      + game.config.stat.rarity.messages[achievements.message_id]),
    (events.rarity, f"???????????????: {events_value:3}%"),
    (talents.rarity, f"???????????????: {talents_value:3}%"),
  ]
  for achievement in ACHIEVEMENT.values():
    granted = achievement.id in st.achievements
    hidden = achievement.hidden and not granted
    symbol = "???" if granted else "??"
    name = "???" if hidden else achievement.name
    description = "????????????" if hidden else achievement.description
    segments.append((achievement.rarity, f"{symbol} {name} - {description}"))
  f = BytesIO()
  make_image(resources.font("sans", 32), segments).save(f, "png")
  await liferestart.send(MessageSegment.image(f))

achievements = subparsers.add_parser("??????", help="?????????????????????")
achievements.set_defaults(func=handle_achievements)


def leaderboard_factory(
  getter: Callable[[Statistics], int], rarities: list[StatRarityItem], suffix: str = ""
):
  async def handler(bot: Bot, event: MessageEvent, args: Namespace):
    leaderboard = sorted(
      ((id, getter(st)) for id, st in STATE.statistics.items()), key=lambda x: x[1], reverse=True)
    segments = []
    ctx = context.get_event_context(event)
    if ctx == -1:
      members: dict[int, str] = {}
    else:
      members = {
        i["user_id"]: i["card"] or i["nickname"]
        for i in await bot.get_group_member_list(group_id=ctx)}
    for id, v in leaderboard:
      judge = Game.judge(v, rarities)
      if id in members:
        name = members[id]
      else:
        name = (await bot.get_stranger_info(user_id=id))["nickname"]
      segments.append((judge.rarity, f"{name} - {v}{suffix}"))
    f = BytesIO()
    make_image(resources.font("sans", 32), segments).save(f, "png")
    await liferestart.send(MessageSegment.image(f))
  return handler


finished_leaderboard = subparsers.add_parser("????????????", help="????????????????????????")
finished_leaderboard.set_defaults(func=leaderboard_factory(
  lambda x: x.finished_games, CONFIG.game.stat.rarity.finished_games))
achievements_leaderboard = subparsers.add_parser("????????????", help="?????????????????????")
achievements_leaderboard.set_defaults(func=leaderboard_factory(
  lambda x: len(x.achievements), CONFIG.game.stat.rarity.achievements))
events_leaderboard = subparsers.add_parser("????????????", help="???????????????????????????")
events_leaderboard.set_defaults(func=leaderboard_factory(
  lambda x: int(len(x.events) / len(EVENT) * 100), CONFIG.game.stat.rarity.event_percentage, "%"))
talents_leaderboard = subparsers.add_parser("????????????", help="???????????????????????????")
talents_leaderboard.set_defaults(func=leaderboard_factory(
  lambda x: int(len(x.talents) / len(TALENT) * 100),
  CONFIG.game.stat.rarity.talent_percentage, "%"))

liferestart = (
  command.CommandBuilder(
    "liferestart", "????????????", "liferestart", "life", "restart", "remake", "??????", "??????")
  .brief("???????????????????????????")
  .shell(parser)
  .build())


@liferestart.handle()
async def handle_liferestart(
  bot: Bot, event: MessageEvent, args: Namespace | ParserExit = ShellCommandArgs()
):
  if isinstance(args, ParserExit):
    await liferestart.finish(args.message)
  await args.func(bot, event, args)
