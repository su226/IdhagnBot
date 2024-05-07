from argparse import Namespace
from typing import Any, Dict, List, Literal, Optional
from urllib.parse import quote as encodeuri

import aiohttp
from aiohttp.http import SERVER_SOFTWARE
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from pydantic import BaseModel, Field

from util import command, configs, misc


class Site(BaseModel):
  origin: str
  post_url: str
  api_url: str
  array_path: str
  id_path: str
  sample_path: str


presets = {
  # Gelbooru (https://gelbooru.com)
  "gelbooru": Site(
    origin="https://gelbooru.com",
    post_url="/index.php?page=post&s=view&id={id}",
    api_url="/index.php?page=dapi&s=post&q=index&tags={tags}&limit={limit}&pid={page}&json=1",
    array_path="/array",
    id_path="/id",
    sample_path="/sample_url",
  ),
  # Danbooru (https://danbooru.donmai.us), Safebooru (https://safebooru.donmai.us)
  "danbooru": Site(
    origin="https://danbooru.donmai.us",
    post_url="/posts/{id}",
    api_url="/posts.json?tags={tags}&limit={limit}&page={page}",
    array_path="/",
    id_path="/id",
    sample_path="/large_file_url",
  ),
  # Konachan R18 (https://konachan.com), Konachan G (https://konachan.net)
  # Yandere (https://yande.re), Lolibooru (https://lolibooru.moe)
  "konachan": Site(
    origin="https://konachan.com",
    post_url="/post/show/{id}",
    api_url="/post.json?tags={tags}&limit={limit}&page={page}",
    array_path="/",
    id_path="/id",
    sample_path="/sample_url",
  ),
  # e621 (https://e621.net), e926 (https://e926.net)
  "e621": Site(
    origin="https://e621.net",
    post_url="/posts/{id}",
    api_url="/posts.json?tags={tags}&limit={limit}&page={page}",
    array_path="/posts",
    id_path="/id",
    sample_path="/sample/url",
  ),
}

EMPTY_PRESET = {
  "origin": None,
  "post_url": None,
  "api_url": None,
  "array_path": None,
  "id_path": None,
  "sample_path": None,
}


class Command(BaseModel):
  command: List[str]
  brief: str = ""
  contexts: List[int] = Field(default_factory=list)
  permission: Literal["member", "admin", "owner", "super"] = "member"
  proxy: Optional[str] = None
  user_agent: str = SERVER_SOFTWARE
  preset: Optional[str] = None
  origin: Optional[str] = None
  post_url: Optional[str] = None
  api_url: Optional[str] = None
  array_path: Optional[str] = None
  id_path: Optional[str] = None
  sample_path: Optional[str] = None

  def to_site(self) -> Site:
    preset = EMPTY_PRESET if self.preset is None else presets[self.preset].model_dump()
    config = self.model_dump()
    return Site.model_validate({
      key: value if config[key] is None else config[key] for key, value in preset.items()})


class Config(BaseModel):
  default_limit: int = 5
  max_limit: int = 10
  presets: Dict[str, Site] = Field(default_factory=dict)
  sites: List[Command] = Field(default_factory=list)


CONFIG = configs.SharedConfig("image_board", Config, False)
config = CONFIG()
presets.update(config.presets)


def get_by_path(root: Dict[str, Any], path: str) -> Any:
  nodes = path.split("/")
  for i in filter(len, nodes):
    root = root[i]
  return root


def register(definition: Command):
  async def handler(args: Namespace = ShellCommandArgs()) -> None:
    if args.limit < 1 or args.limit > config.max_limit:
      await matcher.finish(f"每页图片数必须在 1 和 {config.max_limit} 之间")

    http = misc.http()
    try:
      async with http.get(
        API_URL.format(tags=encodeuri(" ".join(args.tags)), limit=args.limit, page=args.page),
        headers=HEADERS, proxy=definition.proxy,
      ) as response:
        if response.status != 200:
          if response.status == 503:
            await matcher.finish("访问过于频繁，请稍后再试")
          else:
            await matcher.finish(f"HTTP错误: {response.status}")
        data = await response.json()
    except aiohttp.ClientProxyConnectionError as e:
      await matcher.finish(f"别试了我没挂梯子:\n{e}")
    except aiohttp.ClientError as e:
      await matcher.finish(f"网络异常:\n{e}")

    posts = get_by_path(data, site.array_path)
    if not posts:
      await matcher.finish("没有结果")

    message = Message()
    for post in posts:
      url = POST_URL.format(id=get_by_path(post, site.id_path))
      if message:
        url = "\n" + url
      try:
        async with http.get(
          get_by_path(post, site.sample_path), proxy=definition.proxy, headers=HEADERS,
        ) as response:
          img = await response.read()
      except aiohttp.ClientError:
        message.append(MessageSegment.text(url + "\n预览下载失败"))
      else:
        message.append(MessageSegment.text(url))
        message.append(MessageSegment.image(img))

    await matcher.finish(message)
  site = definition.to_site()
  HEADERS = {"User-Agent": definition.user_agent}
  POST_URL = site.origin + site.post_url
  API_URL = site.origin + site.api_url
  parser = ArgumentParser(add_help=False)
  parser.add_argument("tags", nargs="+", metavar="标签")
  parser.add_argument(
    "--limit", "-l", type=int, default=config.default_limit, metavar="图片数",
    help=f"每页的图片数，默认为{config.default_limit}，不能超过{config.max_limit}",
  )
  parser.add_argument("-page", type=int, default=1, metavar="页码")
  builder = (
    command.CommandBuilder(f"image_board.{definition.command[0]}", *definition.command)
    .level(definition.permission)
    .brief(definition.brief)
    .shell(parser))
  if definition.contexts:
    builder.has_group(*definition.contexts)
  matcher = builder.build()
  matcher.handle()(handler)
  return matcher


for site in config.sites:
  register(site)
