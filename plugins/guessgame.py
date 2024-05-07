import math
import random
import re
import time
from collections import Counter
from typing import Dict, List, Tuple

import cairo
import nonebot
from nonebot.adapters.onebot.v11 import Message, MessageEvent, MessageSegment
from nonebot.params import CommandArg
from nonebot.typing import T_State
from pydantic import BaseModel, Field, PrivateAttr

from util import command, configs, context, imutil, misc


class Game(BaseModel):
  colors: int
  pegs: int
  max_guess: int
  correct: Tuple[int, ...]
  guesses: List[Tuple[int, ...]] = Field(default_factory=list)
  begin_time: float = Field(default_factory=time.time)
  _cancelled: bool = PrivateAttr(False)

  @staticmethod
  def new(colors: int = 6, pegs: int = 4, guesses: int = 10) -> "Game":
    colors_seq = range(colors)
    result = tuple(random.choice(colors_seq) for _ in range(pegs))
    return Game(colors=colors, pegs=pegs, max_guess=guesses, correct=result)

  @property
  def success(self) -> bool:
    return bool(self.guesses) and self.guesses[-1] == self.correct

  @property
  def failed(self) -> bool:
    return len(self.guesses) == self.max_guess or self._cancelled

  def render(self) -> MessageSegment:
    hint_cols = math.ceil(self.pegs / 2)
    width = (
      (self.pegs + 2) * PEG_SIZE
      + (self.pegs + 1) * PEG_GAP
      + hint_cols * HINT_SIZE
      + (hint_cols - 1) * HINT_GAP
      + MARGIN * 2
    )
    colors_height = self.colors * PEG_SIZE + (self.colors - 1) * PEG_GAP
    guesses_height = (self.max_guess + 1) * PEG_SIZE + (self.max_guess + 1) * PEG_GAP
    height = max(colors_height, guesses_height) + MARGIN * 2
    with cairo.ImageSurface(cairo.Format.RGB24, width, height) as surface:
      cr = cairo.Context(surface)
      peg_r = PEG_SIZE / 2
      peg_advance = PEG_SIZE + PEG_GAP
      color_x0 = MARGIN + peg_r
      color_y0 = round((height - colors_height) / 2) + peg_r
      guess_x0 = MARGIN + PEG_SIZE * 2 + peg_r
      guess_y0 = round((height - guesses_height) / 2) + peg_r
      hint_r = HINT_SIZE / 2
      hint_h = HINT_SIZE * 2 + HINT_GAP
      hint_x0 = MARGIN + (self.pegs + 2) * PEG_SIZE + (self.pegs + 1) * PEG_GAP + hint_r
      hint_y0 = -hint_h / 2 + hint_r
      hint_advance = HINT_SIZE + HINT_GAP
      cr.rectangle(0, 0, width, height)
      cr.set_source_rgb(*BACKGROUND_COLOR)
      cr.fill()
      cr.set_font_size(FONT_SIZE)
      cr.set_line_width(1)
      for i, color in zip(range(self.colors), COLORS):
        peg_y = color_y0 + i * peg_advance
        cr.arc(color_x0, peg_y, peg_r, 0, 360)
        cr.set_source_rgb(*color)
        cr.fill_preserve()
        cr.set_source_rgb(*BORDER_COLOR)
        cr.stroke()
        i_str = str(i + 1)
        extents = cr.text_extents(i_str)
        cr.move_to(color_x0 - extents.x_advance / 2, peg_y + extents.height / 2)
        cr.show_text(i_str)
        cr.new_path()
      for y, guess in enumerate(self.guesses):
        peg_y = guess_y0 + y * peg_advance
        for x, color in enumerate(guess):
          peg_x = guess_x0 + x * peg_advance
          cr.arc(peg_x, peg_y, peg_r, 0, 360)
          cr.set_source_rgb(*COLORS[color])
          cr.fill_preserve()
          cr.set_source_rgb(*BORDER_COLOR)
          cr.stroke()
        correct_pos, correct_color = self.count_correct(guess)
        for i in range(self.pegs):
          hy, hx = divmod(i, hint_cols)
          hint_x = hint_x0 + hint_advance * hx
          hint_y = peg_y + hint_y0 + hint_advance * hy
          cr.arc(hint_x, hint_y, hint_r, 0, 360)
          if i >= correct_pos + correct_color:
            cr.set_source_rgb(*DARK_COLOR)
            cr.fill()
          elif i >= correct_pos:
            cr.set_source_rgb(*CORRECT_COLOR_COLOR)
            cr.fill_preserve()
            cr.set_source_rgb(*BORDER_COLOR)
            cr.stroke()
          else:
            cr.set_source_rgb(*CORRECT_POS_COLOR)
            cr.fill_preserve()
            cr.set_source_rgb(*BORDER_COLOR)
            cr.stroke()
      for y in range(len(self.guesses), self.max_guess):
        peg_y = guess_y0 + y * peg_advance
        for x in range(self.pegs):
          peg_x = guess_x0 + x * peg_advance
          cr.arc(peg_x, peg_y, peg_r, 0, 360)
          cr.set_source_rgb(*DARK_COLOR)
          cr.fill()
        for i in range(self.pegs):
          hy, hx = divmod(i, hint_cols)
          hint_x = hint_x0 + hint_advance * hx
          hint_y = peg_y + hint_y0 + hint_advance * hy
          cr.arc(hint_x, hint_y, hint_r, 0, 360)
          cr.set_source_rgb(*DARK_COLOR)
          cr.fill()
      line_x = MARGIN + PEG_SIZE * 2
      line_y = MARGIN + peg_advance * self.max_guess
      line_w = PEG_SIZE * self.pegs + PEG_GAP * (self.pegs - 1)
      if self.success or self.failed:
        peg_y = guess_y0 + self.max_guess * peg_advance + PEG_GAP
        for i, color in enumerate(self.correct):
          peg_x = guess_x0 + i * peg_advance
          cr.arc(peg_x, peg_y, peg_r, 0, 360)
          cr.set_source_rgb(*COLORS[color])
          cr.fill_preserve()
          cr.set_source_rgb(*BORDER_COLOR)
          cr.stroke()
      else:
        cr.rectangle(line_x, line_y + PEG_GAP, line_w, PEG_SIZE)
        cr.set_source_rgb(*DARK_COLOR)
        cr.fill()
      cr.move_to(line_x, line_y)
      cr.line_to(line_x + line_w, line_y)
      cr.set_source_rgb(*DARK_COLOR)
      cr.set_line_width(2)
      cr.stroke()
      return imutil.to_segment(surface)

  def count_correct(self, guess: Tuple[int, ...]) -> Tuple[int, int]:
    correct_pos = sum(x == y for x, y in zip(self.correct, guess))
    correct = Counter(self.correct) & Counter(guess)
    return correct_pos, sum(correct.values()) - correct_pos


class State(BaseModel):
  current_games: Dict[int, Game] = Field(default_factory=dict)


STATE = configs.SharedState("guessgame", State)
EMPTY_RE = re.compile(r"\s+")
USAGE = (
  "发送 {} 个数字猜颜色，可能有重复的，右边的黑点是位置和颜色都对，白点是只有颜色对；"
  "发送「/猜颜色 放弃」放弃游戏。"
)
STANDARD = (6, 4, 10)
SUPER = (8, 5, 12)
PEG_SIZE = 32
FONT_SIZE = PEG_SIZE * 0.6
PEG_GAP = round(PEG_SIZE * 0.1)
HINT_SIZE = round(PEG_SIZE * 0.35)
HINT_GAP = round(HINT_SIZE * 0.1)
MARGIN = round(PEG_SIZE * 0.5)
BACKGROUND_COLOR = (0.9, 0.9, 0.9)
DARK_COLOR = (0.6, 0.6, 0.6)
BORDER_COLOR = (0.0, 0.0, 0.0)
CORRECT_POS_COLOR = (0.0, 0.0, 0.0)
CORRECT_COLOR_COLOR = (1.0, 1.0, 1.0)
COLORS = [
  (1.0, 0.0, 0.0),
  (1.0, 1.0, 0.0),
  (0.0, 1.0, 0.0),
  (0.2, 0.3, 1.0),
  (1.0, 0.5, 0.0),
  (0.5, 0.0, 0.7),
  (0.5, 0.3, 0.3),
  (0.4, 0.8, 1.0),
  (0.7, 1.0, 0.7),
  (1.0, 0.6, 1.0),
]

guessgame = (
  command.CommandBuilder("guessgame", "猜颜色")
  .brief("猜颜色小游戏")
  .usage((
    "/猜颜色 - 开始标准游戏\n"
    "/猜颜色 困难 - 开始困难游戏\n"
    "/猜颜色 放弃 - 放弃游戏\n"
    "标准为6种颜色4个珠子10次机会，困难为8种颜色5个珠子12次机会。\n"
    "一个群里只能同时有一局猜颜色小游戏，所有人都可以参与。\n"
    "参考自 Simon Tatham's Portable Puzzle Collection。"
  ))
  .build()
)
@guessgame.handle()
async def handle_guessgame(event: MessageEvent, arg: Message = CommandArg()) -> None:
  state = STATE()
  game_id = context.get_event_context(event)
  if game_id == -1:
    game_id = -event.user_id
  arg_str = str(arg).rstrip()
  if arg_str == "放弃":
    if game_id in state.current_games:
      game = state.current_games.pop(game_id)
      STATE.dump()
      game._cancelled = True
      img = await misc.to_thread(game.render)
      await guessgame.finish("已结束游戏" + img)
    else:
      await guessgame.finish("当前没有猜颜色游戏")
  if game_id not in state.current_games:
    if arg_str in ("困难", "高级"):
      colors, pegs, guesses = SUPER
    else:
      colors, pegs, guesses = STANDARD
    game = Game.new(colors, pegs, guesses)
    state.current_games[game_id] = game
    STATE.dump()
    msg = "游戏开始，" + USAGE.format(game.pegs)
  else:
    game = state.current_games[game_id]
    msg = "本群已经有一局猜颜色了" + USAGE.format(game.pegs)
  img = await misc.to_thread(game.render)
  await guessgame.finish(msg + img)


def check_guess_one(event: MessageEvent, bot_state: T_State) -> bool:
  state = STATE()
  game_id = context.get_event_context(event)
  if game_id == -1:
    game_id = -event.user_id
  if game_id in state.current_games:
    game = state.current_games[game_id]
    number_str = EMPTY_RE.sub("", str(event.message))
    if len(number_str) == game.pegs:
      numbers = tuple(ord(x) - 49 for x in number_str)
      bot_state["numbers"] = numbers
      return all(0 <= x < game.colors for x in numbers)
  return False
guess_one = nonebot.on_message(check_guess_one)
@guess_one.handle()
async def handle_guess_one(event: MessageEvent, bot_state: T_State) -> None:
  state = STATE()
  game_id = context.get_event_context(event)
  if game_id == -1:
    game_id = -event.user_id
  game = state.current_games[game_id]
  numbers: Tuple[int] = bot_state["numbers"]
  game.guesses.append(numbers)
  if game.success:
    msg = f"胜利，本局总用时 {misc.format_time(time.time() - game.begin_time)}"
    del state.current_games[game_id]
  elif game.failed:
    msg = "游戏失败"
    del state.current_games[game_id]
  else:
    msg = USAGE.format(game.pegs)
  STATE.dump()
  img = await misc.to_thread(game.render)
  await guess_one.finish(msg + img)
