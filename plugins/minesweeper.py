import itertools
import random
import re
import time
from typing import Any, Dict, Generator, List, Tuple

import cairo
import nonebot
from nonebot.adapters.onebot.v11 import Message, MessageEvent, MessageSegment
from nonebot.params import CommandArg
from nonebot.typing import T_State
from pydantic import BaseModel, Field, PrivateAttr

from util import command, configs, context, imutil, misc


class Game(BaseModel):
  width: int
  height: int
  mine_count: int
  mines: List[List[int]]
  state: List[List[int]]
  dig_count: int = 0
  begin_time: float = 0
  _failed: bool = PrivateAttr(False)

  @staticmethod
  def new(width: int, height: int, mines: int) -> "Game":
    return Game(
      width=width,
      height=height,
      mine_count=mines,
      mines=[[0] * width for _ in range(height)],
      state=[[0] * width for _ in range(height)],
    )

  @property
  def success(self) -> bool:
    return self.dig_count == self.width * self.height - self.mine_count

  def dig(self, y0: int, x0: int) -> None:
    if self.dig_count == 0:
      self.begin_game(y0, x0)
    cell = self.state[y0][x0]
    mines = self.mines[y0][x0]
    if cell == 0:
      self.state[y0][x0] = 1
      self.dig_count += 1
      if mines == -1:
        self._failed = True
      elif mines == 0:
        for y, x in neighbors(self.state, y0, x0):
          if self.state[y][x] == 0:
            self.dig(y, x)
    elif cell == 1 and mines > 0:
      flags = sum(self.state[y][x] == 2 for y, x in neighbors(self.state, y0, x0))
      if flags >= mines:
        for y, x in neighbors(self.state, y0, x0):
          if self.state[y][x] == 0:
            self.dig(y, x)

  def flag(self, y0: int, x0: int) -> None:
    value = self.state[y0][x0]
    if value == 1:
      return
    self.state[y0][x0] = 2 if value == 0 else 0

  def begin_game(self, y0: int, x0: int) -> None:
    for y, x in random.sample([
      p for p in itertools.product(range(self.height), range(self.width)) if p != (y0, x0)
    ], self.mine_count):
      self.mines[y][x] = -1
    for y, row in enumerate(self.mines):
      for x, col in enumerate(row):
        if col != -1:
          self.mines[y][x] = sum(self.mines[y][x] == -1 for y, x in neighbors(self.mines, y, x))
    self.begin_time = time.time()

  def render(self, *highlights: Tuple[int, int]) -> MessageSegment:
    width = self.width * CELL_SIZE + BOARD_BORDER * 2 + BOARD_MARGIN * 2
    height = self.height * CELL_SIZE + BOARD_BORDER * 2 + BOARD_MARGIN * 2
    with cairo.ImageSurface(cairo.Format.RGB24, width, height) as surface:
      cr = cairo.Context(surface)
      cr.rectangle(0, 0, width, height)
      cr.set_source_rgb(*BACKGROUND_COLOR)
      cr.fill()
      board_w = CELL_SIZE * self.width + BOARD_BORDER * 2
      board_h = CELL_SIZE * self.height + BOARD_BORDER * 2
      cr.rectangle(BOARD_MARGIN, BOARD_MARGIN, board_w, board_h)
      cr.set_source_rgb(*BOARD_COLOR)
      cr.fill()
      draw_border(cr, BOARD_MARGIN, BOARD_MARGIN, board_w, board_h, BOARD_BORDER, True)
      regular_font = cairo.ToyFontFace("sans")
      bold_font = cairo.ToyFontFace("sans", cairo.FontSlant.NORMAL, cairo.FontWeight.BOLD)
      success = self.success
      for y in range(self.height):
        for x in range(self.width):
          cell_x = BOARD_MARGIN + BOARD_BORDER + x * CELL_SIZE
          cell_y = BOARD_MARGIN + BOARD_BORDER + y * CELL_SIZE
          if self.state[y][x] == 1:
            cr.rectangle(cell_x, cell_y, CELL_SIZE, 1)
            cr.rectangle(cell_x, cell_y + 1, 1, CELL_SIZE - 1)
            cr.set_source_rgb(*DARK_COLOR)
            cr.fill()
            count = self.mines[y][x]
            if count == -1:
              cr.rectangle(cell_x + 1, cell_y + 1, CELL_SIZE - 1, CELL_SIZE - 1)
              cr.set_source_rgb(*MINE_BACKGROUND_COLOR)
              cr.fill()
              draw_mine(cr, cell_x, cell_y)
            elif count > 0:
              cr.set_font_face(bold_font)
              cr.set_font_size(FONT_SIZE)
              extents = cr.text_extents(str(count))
              cr.move_to(
                cell_x + (CELL_SIZE - extents.x_advance) / 2,
                cell_y + (CELL_SIZE + extents.height) / 2,
              )
              cr.set_source_rgb(*COLORS[count - 1])
              cr.show_text(str(count))
            else:
              draw_pos(cr, regular_font, y, x, cell_y, cell_x)
          elif self._failed and self.mines[y][x] == -1 and self.state[y][x] != 2:
            cr.rectangle(cell_x, cell_y, CELL_SIZE, 1)
            cr.rectangle(cell_x, cell_y + 1, 1, CELL_SIZE - 1)
            cr.set_source_rgb(*DARK_COLOR)
            cr.fill()
            draw_mine(cr, cell_x, cell_y)
          else:
            cr.rectangle(cell_x, cell_y, CELL_SIZE, CELL_SIZE)
            cr.set_source_rgb(*CELL_COLOR)
            cr.fill()
            draw_border(cr, cell_x, cell_y, CELL_SIZE, CELL_SIZE, CELL_BORDER)
            if self.state[y][x] == 2 or success:
              draw_flag(cr, cell_x, cell_y)
              if self._failed and self.mines[y][x] != -1:
                draw_cross(cr, cell_x, cell_y)
            else:
              draw_pos(cr, regular_font, y, x, cell_y, cell_x)
      cr.set_font_face(regular_font)
      cr.set_font_size(FONT_SIZE * .5)
      cr.set_source_rgb(*DARKER_COLOR)
      for x in range(self.width):
        cell_x = BOARD_MARGIN + BOARD_BORDER + x * CELL_SIZE
        x_str = str(x + 1)
        extents = cr.text_extents(x_str)
        cr.move_to(
          cell_x + (CELL_SIZE - extents.x_advance) / 2,
          BOARD_MARGIN - BOARD_BORDER,
        )
        cr.show_text(x_str)
        cr.move_to(
          cell_x + (CELL_SIZE - extents.x_advance) / 2,
          BOARD_MARGIN + board_h + BOARD_BORDER + extents.height,
        )
        cr.show_text(x_str)
      for y in range(self.height):
        cell_y = BOARD_MARGIN + BOARD_BORDER + y * CELL_SIZE
        y_str = to_base26(y + 1)
        extents = cr.text_extents(y_str)
        cr.move_to(
          BOARD_MARGIN - extents.x_advance - BOARD_BORDER,
          cell_y + (CELL_SIZE + extents.height) / 2,
        )
        cr.show_text(y_str)
        cr.move_to(
          BOARD_MARGIN + board_w + BOARD_BORDER,
          cell_y + (CELL_SIZE + extents.height) / 2,
        )
        cr.show_text(y_str)
      for x in range(5, self.width, 5):
        line_x = BOARD_MARGIN + BOARD_BORDER + x * CELL_SIZE
        line_y = BOARD_MARGIN + BOARD_BORDER
        cr.move_to(line_x, line_y)
        cr.line_to(line_x, line_y + CELL_SIZE * self.height)
      for y in range(5, self.height, 5):
        line_x = BOARD_MARGIN + BOARD_BORDER
        line_y = BOARD_MARGIN + BOARD_BORDER + y * CELL_SIZE
        cr.move_to(line_x, line_y)
        cr.line_to(line_x + CELL_SIZE * self.width, line_y)
      cr.stroke()
      for hy, hx in highlights:
        cell_x = BOARD_MARGIN + BOARD_BORDER + hx * CELL_SIZE
        cell_y = BOARD_MARGIN + BOARD_BORDER + hy * CELL_SIZE
        cr.rectangle(cell_x, cell_y, CELL_SIZE, CELL_SIZE)
      cr.set_source_rgb(*CURSOR_COLOR)
      cr.stroke()
      return imutil.to_segment(surface)


class State(BaseModel):
  current_games: Dict[int, Game] = Field(default_factory=dict)


STATE = configs.SharedState("minesweeper", State)
DIG_RE = re.compile(r"(?:\s*(挖|旗|dig|flag)\s*(?:([A-Za-z]+)\s*(\d+)\s*)+)+")
SPLIT_RE = re.compile(r"(?:挖|旗|dig|flag|([A-Za-z]+)\s*(\d+))")
USAGE = (
  "发送“挖<行列>”挖开格子（可以挖空格），发送“旗<行列>”放置或移除旗标，如“挖A1”或者“旗B2”；"
  "发送「/扫雷 放弃」放弃游戏。"
)
EASY = (9, 9, 10)
MEDIUM = (16, 16, 40)
HARD = (30, 16, 99)
CELL_SIZE = 40
FONT_SIZE = CELL_SIZE * .875
CELL_BORDER = max(round(CELL_SIZE * .1), 1)
BOARD_BORDER = max(round(CELL_SIZE * .15), 1)
BOARD_MARGIN = round(CELL_SIZE * 1.35)
BACKGROUND_COLOR = (0.9, 0.9, 0.9)
BOARD_COLOR = (0.855, 0.855, 0.855)
CELL_COLOR = (0.9, 0.9, 0.9)
LIGHT_COLOR = (1.0, 1.0, 1.0)
DARK_COLOR = (0.6, 0.6, 0.6)
DARKER_COLOR = (0.3, 0.3, 0.3)
MINE_COLOR = (0.0, 0.0, 0.0)
MINE_BACKGROUND_COLOR = (1.0, 0.0, 0.0)
FLAG_COLOR = (1.0, 0.0, 0.0)
FLAG_BASE_COLOR = (0.0, 0.0, 0.0)
CROSS_COLOR = (1.0, 0.0, 0.0)
CURSOR_COLOR = (0, 0, 1)
COLORS = [
  (0.0, 0.0, 1.0),
  (0.0, 0.5, 0.0),
  (1.0, 0.0, 0.0),
  (0.0, 0.0, 0.5),
  (0.5, 0.0, 0.0),
  (0.0, 0.5, 0.5),
  (0.0, 0.0, 0.0),
  (0.5, 0.5, 0.5),
]


def to_base26(v: int) -> str:
  result = ""
  while v:
    v, mod = divmod(v, 26)
    result = chr(64 + mod) + result
  return result


def from_base26(v: str) -> int:
  result = 0
  for i in v:
    result = result * 26 + ord(i) - 64
  return result


def neighbors(board: List[List[int]], y0: int, x0: int) -> Generator[Tuple[int, int], None, None]:
  yield from (
    (y, x) for y, x in [
      (y0 - 1, x0 - 1),
      (y0 - 1, x0),
      (y0 - 1, x0 + 1),
      (y0, x0 - 1),
      (y0, x0 + 1),
      (y0 + 1, x0 - 1),
      (y0 + 1, x0),
      (y0 + 1, x0 + 1),
    ] if 0 <= y < len(board) and 0 <= x < len(board[0])
  )


def draw_border(
  cr: "cairo.Context[Any]", x: float, y: float, w: float, h: float, b: float,
  reverse: bool = False,
) -> None:
  cr.move_to(x, y)
  cr.line_to(x + w, y)
  cr.line_to(x + w - b, y + b)
  cr.line_to(x + b, y + b)
  cr.line_to(x + b, y + h - b)
  cr.line_to(x, y + h)
  if reverse:
    cr.set_source_rgb(*DARK_COLOR)
  else:
    cr.set_source_rgb(*LIGHT_COLOR)
  cr.fill()
  cr.move_to(x + w, y + h)
  cr.line_to(x, y + h)
  cr.line_to(x + b, y + h - b)
  cr.line_to(x + w - b, y + h - b)
  cr.line_to(x + w - b, y + b)
  cr.line_to(x + w, y)
  if reverse:
    cr.set_source_rgb(*LIGHT_COLOR)
  else:
    cr.set_source_rgb(*DARK_COLOR)
  cr.fill()


def draw_flag(cr: "cairo.Context[Any]", x: float, y: float) -> None:
  def coord(x1: float, y1: float) -> Tuple[float, float]:
    return x + x1 * CELL_SIZE, y + y1 * CELL_SIZE
  cr.move_to(*coord(.6, .5))
  cr.line_to(*coord(.6, .7))
  cr.line_to(*coord(.8, .8))
  cr.line_to(*coord(.25, .8))
  cr.line_to(*coord(.55, .7))
  cr.line_to(*coord(.55, .45))
  cr.set_source_rgb(*FLAG_BASE_COLOR)
  cr.fill()
  cr.move_to(*coord(.6, .2))
  cr.line_to(*coord(.6, .5))
  cr.line_to(*coord(.2, .35))
  cr.set_source_rgb(*FLAG_COLOR)
  cr.fill()


def draw_cross(cr: "cairo.Context[Any]", x: float, y: float) -> None:
  line = round(.1 * CELL_SIZE)
  cr.move_to(x + CELL_BORDER, y + CELL_BORDER)
  cr.line_to(x + CELL_BORDER + line, y + CELL_BORDER)
  cr.line_to(x + CELL_SIZE - CELL_BORDER, y + CELL_SIZE - CELL_BORDER - line)
  cr.line_to(x + CELL_SIZE - CELL_BORDER, y + CELL_SIZE - CELL_BORDER)
  cr.line_to(x + CELL_SIZE - CELL_BORDER - line, y + CELL_SIZE - CELL_BORDER)
  cr.line_to(x + CELL_BORDER, y + CELL_BORDER + line)
  cr.move_to(x + CELL_SIZE - CELL_BORDER, y + CELL_BORDER)
  cr.line_to(x + CELL_SIZE - CELL_BORDER, y + CELL_BORDER + line)
  cr.line_to(x + CELL_BORDER + line, y + CELL_SIZE - CELL_BORDER)
  cr.line_to(x + CELL_BORDER, y + CELL_SIZE - CELL_BORDER)
  cr.line_to(x + CELL_BORDER, y + CELL_SIZE - CELL_BORDER - line)
  cr.line_to(x + CELL_SIZE - CELL_BORDER - line, y + CELL_BORDER)
  cr.set_source_rgb(*CROSS_COLOR)
  cr.fill()


def draw_mine(cr: "cairo.Context[Any]", x: float, y: float) -> None:
  cx = x + 0.5 + CELL_SIZE / 2
  cy = y + 0.5 + CELL_SIZE / 2
  r = CELL_SIZE / 2 - 3
  cr.arc(cx, cy, r * 5 / 6, 0, 360)
  rect_w = round(r)
  rect_r = round(r / 6)
  if not cx.is_integer():
    rect_w += 0.5
    rect_r += 0.5
  cr.rectangle(cx - rect_r, cy - rect_w, rect_r * 2, rect_w * 2)
  cr.rectangle(cx - rect_w, cy - rect_r, rect_w * 2, rect_r * 2)
  cr.set_source_rgb(*MINE_COLOR)
  cr.fill()
  cr.rectangle(round(cx - r / 3), round(cy - r / 3), round(r / 3), round(r / 4))
  cr.set_source_rgb(*LIGHT_COLOR)
  cr.fill()


def draw_pos(
  cr: "cairo.Context[Any]", font: cairo.FontFace, y: int, x: int, cell_y: int, cell_x: int,
) -> None:
  xy_str = f"{to_base26(y + 1)}{x + 1}"
  cr.set_font_face(font)
  cr.set_font_size(FONT_SIZE / 2)
  extents = cr.text_extents(xy_str)
  cr.move_to(
    cell_x + (CELL_SIZE - extents.x_advance) / 2,
    cell_y + (CELL_SIZE + extents.height) / 2,
  )
  cr.set_source_rgb(*DARK_COLOR)
  cr.show_text(xy_str)


minesweeper = (
  command.CommandBuilder("minesweeper", "扫雷")
  .brief("扫雷小游戏")
  .usage((
    "/扫雷 [难度] - 开始标准游戏（默认为初级）\n"
    "/扫雷 <宽度> <高度> <雷数> - 开始自定义游戏\n"
    "/扫雷 放弃 - 放弃游戏\n"
    "难度可以是“初级”（9x9，16个雷）、“中级”（16x16，40个雷）、“高级”（30x16，99个雷）\n"
    "一个群里只能同时有一局扫雷小游戏，所有人都可以参与。\n"
    "参考自 Simon Tatham's Portable Puzzle Collection。"
  ))
  .build()
)
@minesweeper.handle()
async def handle_minesweeper(event: MessageEvent, arg: Message = CommandArg()) -> None:
  state = STATE()
  game_id = context.get_event_context(event)
  if game_id == -1:
    game_id = -event.user_id
  arg_str = str(arg).rstrip()
  if arg_str == "放弃":
    if game_id in state.current_games:
      game = state.current_games.pop(game_id)
      STATE.dump()
      game._failed = True
      img = await misc.to_thread(game.render)
      await minesweeper.finish("已结束游戏" + img)
    else:
      await minesweeper.finish("当前没有扫雷游戏")
  if game_id not in state.current_games:
    try:
      width, height, mines = map(int, arg_str.split(maxsplit=2))
      errors = []
      if not 8 <= width <= 30:
        errors.append("宽度必须在 8 和 30 之间")
      if not 8 <= height <= 30:
        errors.append("高度必须在 8 和 24 之间")
      max_mines_orig = width * height * 0.9
      max_mines = int(max_mines_orig)
      if not 10 <= mines <= max_mines_orig:
        symbol = "=" if max_mines == max_mines_orig else "≈"
        mines_expr = f"{width} × {height} × 90% {symbol} {max_mines}"
        errors.append(f"雷数必须在 10 和格子数的 90%（{mines_expr}）之间")
      if errors:
        await minesweeper.finish("\n".join(errors))
    except ValueError:
      if arg_str == "高级":
        width, height, mines = HARD
      elif arg_str == "中级":
        width, height, mines = MEDIUM
      else:
        width, height, mines = EASY
    game = Game.new(width, height, mines)
    state.current_games[game_id] = game
    STATE.dump()
    msg = f"游戏开始，{width} 行，{height} 列，{mines} 个雷，{USAGE}"
  else:
    game = state.current_games[game_id]
    msg = f"本群已经有一局扫雷了，{USAGE}"
  img = await misc.to_thread(game.render)
  await minesweeper.finish(msg + img)


def check_dig(event: MessageEvent, bot_state: T_State) -> bool:
  def repl(match: re.Match[str]) -> str:
    text = match[0]
    nonlocal op
    if text in {"挖", "dig"}:
      op = 0
    elif text in {"旗", "flag"}:
      op = 1
    else:
      ops.append((op, from_base26(match[1].upper()) - 1, int(match[2]) - 1))
    return text
  state = STATE()
  game_id = context.get_event_context(event)
  if game_id == -1:
    game_id = -event.user_id
  if game_id in state.current_games:
    text = str(event.message)
    if DIG_RE.fullmatch(text):
      op = 0
      ops: List[Tuple[int, int, int]] = []
      SPLIT_RE.sub(repl, text)
      bot_state["ops"] = ops
      return True
  return False
dig = nonebot.on_message(check_dig)
@dig.handle()
async def handle_dig(event: MessageEvent, bot_state: T_State) -> None:
  state = STATE()
  game_id = context.get_event_context(event)
  if game_id == -1:
    game_id = -event.user_id
  game = state.current_games[game_id]
  lines: List[str] = []
  highlights: List[Tuple[int, int]] = []
  ops: List[Tuple[int, int, int]] = bot_state["ops"]
  for op, y, x in ops:
    if not (0 <= x < game.width and 0 <= y < game.height):
      lines.append(f"{to_base26(y + 1)}{x + 1} 超出范围")
      continue
    highlights.append((y, x))
    if op:
      game.flag(y, x)
    else:
      game.dig(y, x)
    if game._failed:
      del state.current_games[game_id]
      lines.append("游戏失败")
      break
    elif game.success:
      del state.current_games[game_id]
      lines.append(f"胜利，本局总用时 {misc.format_time(time.time() - game.begin_time)}")
      break
  else:
    lines.append(USAGE)
  STATE.dump()
  img = await misc.to_thread(game.render, *highlights)
  await dig.finish("\n".join(lines) + img)
