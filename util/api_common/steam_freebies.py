from dataclasses import dataclass
import enum
from html.parser import HTMLParser
from typing import Optional

from pydantic import BaseModel

from util import misc

__all__ = ["Game", "URL_BASE", "get_freebies"]
API = "https://store.steampowered.com/search/results/?query&maxprice=free&specials=1&infinite=1"
URL_BASE = "https://store.steampowered.com/app/"


class ApiResult(BaseModel):
  results_html: str


@dataclass
class Game:
  appid: int
  name: str
  image: str


class ParserMode(enum.Enum):
  NONE = enum.auto()
  NAME = enum.auto()


class Parser(HTMLParser):
  def __init__(self) -> None:
    super().__init__()
    self.games: list[Game] = []
    self.mode = ParserMode.NONE

  def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
    if tag == "a":
      self.game = Game(0, "", "")
      for key, value in attrs:
        if key == "data-ds-appid":
          if value:
            self.game.appid = int(value)
          break
    elif tag == "img":
      for key, value in attrs:
        if key == "srcset":
          if value:
            self.game.image = value.split(",")[-1].split()[0]
          break
    else:
      classes: set[str] = set()
      for key, value in attrs:
        if key == "class":
          if value:
            classes.update(value.split())
          break
      if "title" in classes:
        self.mode = ParserMode.NAME

  def handle_endtag(self, tag: str) -> None:
    self.mode = ParserMode.NONE
    if tag == "a":
      self.games.append(self.game)

  def handle_data(self, data: str) -> None:
    if self.mode == ParserMode.NAME:
      self.game.name = data

  @staticmethod
  def parse(data: str) -> list[Game]:
    parser = Parser()
    parser.feed(data)
    parser.close()
    return parser.games


async def get_freebies() -> list[Game]:
  async with misc.http().get(API) as response:
    data = ApiResult.model_validate(await response.json())
  return Parser.parse(data.results_html)
