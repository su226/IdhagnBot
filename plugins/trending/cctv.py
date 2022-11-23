import json
from typing import List

from util import misc

from .common import Item

API = "https://news.cctv.com/2019/07/gaiban/cmsdatainterface/page/news_1.jsonp"


async def get_data() -> List[Item]:
  http = misc.http()
  async with http.get(API) as response:
    data = await response.text()
  # strip jsonp news()
  data = json.loads(data[5:-1])
  result = []
  for i in data["data"]["list"]:
    result.append(Item(
      url=i["url"],
      title=i["title"],
      image=i["image"],
      content=i["brief"],
    ))
  return result
