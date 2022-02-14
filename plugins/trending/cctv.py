from aiohttp import ClientSession
from .common import Item
import json

API = "https://news.cctv.com/2019/07/gaiban/cmsdatainterface/page/news_1.jsonp"

async def get_data() -> list[Item]:
  async with ClientSession() as http:
    response = await http.get(API)
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
