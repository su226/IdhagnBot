import json
from html.parser import HTMLParser
from typing import List, Optional, Tuple
from urllib.parse import unquote as decodeuri

from util import misc

from .common import Item

URL = "https://www.baidu.com"


class Parser(HTMLParser):
  def __init__(self):
    super().__init__()
    self.got = False
    self.data = {}

  def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
    for _, value in attrs:
      if value == "hotsearch_data":
        self.got = True
        break

  def handle_data(self, data: str):
    if self.got:
      self.data = json.loads(data)
      self.got = False


def extract_data(value: str):
  parser = Parser()
  parser.feed(value)
  parser.close()
  return parser.data


async def get_data() -> List[Item]:
  http = misc.http()
  async with http.get(URL, headers={"User-Agent": misc.BROWSER_UA}) as response:
    data = extract_data(await response.text())
  result = []
  for i in data["hotsearch"]:
    result.append(Item(
      url=decodeuri(i["linkurl"]),
      title=i["pure_title"],
      image="",
      content="百度热搜|热度" + str(i["heat_score"])
    ))
  return result
