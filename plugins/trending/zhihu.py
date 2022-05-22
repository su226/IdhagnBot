from aiohttp import ClientSession

from .common import Item

API = "https://api.zhihu.com/topstory/hot-list"
URL = "https://www.zhihu.com/question/{}"


async def get_data() -> list[Item]:
  async with ClientSession() as http:
    response = await http.get(API)
    data = await response.json()
  result = []
  for i in data["data"]:
    result.append(Item(
      url=URL.format(i["target"]["id"]),
      title=i["target"]["title"],
      image=i["children"][0]["thumbnail"],
      content=i["detail_text"] + "|" + i["target"]["excerpt"]
    ))
  return result
