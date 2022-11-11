import json
from html.parser import HTMLParser
from urllib.parse import unquote

from util import misc

from .common import Item

URL = "https://www.baidu.com"
UA = "Mozilla/5.0 (X11; Linux x86_64; rv:97.0) Gecko/20100101 Firefox/97.0"


class Parser(HTMLParser):
  def __init__(self):
    super().__init__()
    self.got = False
    self.data = {}

  def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
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


async def get_data() -> list[Item]:
  http = misc.http()
  async with http.get(URL, headers={"User-Agent": UA}) as response:
    data = extract_data(await response.text())
  result = []
  for i in data["hotsearch"]:
    result.append(Item(
      url=unquote(i["linkurl"]),
      title=i["pure_title"],
      image="",
      content="百度热搜|热度" + str(i["heat_score"])
    ))
  return result
