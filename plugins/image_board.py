import base64
from argparse import Namespace
from typing import Any, Literal

import aiohttp
from aiohttp.http import SERVER_SOFTWARE
from nonebot.adapters.onebot.v11 import Message
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from pydantic import BaseModel, Field

from util import command
from util.config import BaseConfig


class Site(BaseModel):
  origin: str
  post_url: str
  api_url: str
  array_path: str
  id_path: str
  sample_path: str


presets = {
  "gelbooru": Site(  # Gelbooru (https://gelbooru.com)
    origin="https://gelbooru.com",
    post_url="/index.php?page=post&s=view&id={id}",
    api_url="/index.php?page=dapi&s=post&q=index&tags={tags}&limit={limit}&pid={page}&json=1",
    array_path="/array",
    id_path="/id",
    sample_path="/sample_url"
  ),
  # Danbooru (https://danbooru.donmai.us), Safebooru (https://safebooru.donmai.us)
  "danbooru": Site(
    origin="https://danbooru.donmai.us",
    post_url="/posts/{id}",
    api_url="/posts.json?tags={tags}&limit={limit}&page={page}",
    array_path="/",
    id_path="/id",
    sample_path="/large_file_url"
  ),
  # Konachan R18 (https://konachan.com), Konachan G (https://konachan.net)
  # Yandere (https://yande.re)
  "konachan": Site(
    origin="https://konachan.com",
    post_url="/post/show/{id}",
    api_url="/post.json?tags={tags}&limit={limit}&page={page}",
    array_path="/",
    id_path="/id",
    sample_path="/sample_url"
  ),
  "e621": Site(  # e621 (https://e621.net), e926 (https://e926.net)
    origin="https://e621.net",
    post_url="/posts/{id}",
    api_url="/posts.json?tags={tags}&limit={limit}&page={page}",
    array_path="/posts",
    id_path="/id",
    sample_path="/sample/url"
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
  command: list[str]
  brief: str = ""
  contexts: list[int] = Field(default_factory=list)
  permission: Literal["member", "admin", "owner", "super"] = "member"
  proxy: str | None = None
  user_agent: str = SERVER_SOFTWARE
  preset: str | None = None
  origin: str | None = None
  post_url: str | None = None
  api_url: str | None = None
  array_path: str | None = None
  id_path: str | None = None
  sample_path: str | None = None

  def to_site(self) -> Site:
    preset = EMPTY_PRESET if self.preset is None else presets[self.preset].dict()
    config = self.dict()
    return Site.parse_obj({
      key: value if config[key] is None else config[key] for key, value in preset.items()})


class Config(BaseConfig):
  __file__ = "image_board"
  default_limit: int = 5
  max_limit: int = 10
  presets: dict[str, Site] = Field(default_factory=dict)
  sites: list[Command] = Field(default_factory=list)


CONFIG = Config.load()
presets.update(CONFIG.presets)


def get_by_path(root: dict, path: str) -> Any:
  nodes = path.split("/")
  for i in filter(len, nodes):
    root = root[i]
  return root


def register(definition: Command):
  async def handler(args: Namespace | ParserExit = ShellCommandArgs()):
    if isinstance(args, ParserExit):
      await matcher.finish(args.message)
    if args.limit < 1 or args.limit > CONFIG.max_limit:
      await matcher.finish(f"每页图片数必须在 1 和 {CONFIG.max_limit} 之间")
    async with aiohttp.ClientSession(headers=HEADERS) as http:
      try:
        response = await http.get(
          API_URL.format(tags=" ".join(args.tags), limit=args.limit, page=args.page),
          proxy=definition.proxy)
      except aiohttp.ClientProxyConnectionError as e:
        await matcher.finish(f"别试了我没挂梯子:\n{e}")
      except aiohttp.ClientError as e:
        await matcher.finish(f"网络异常:\n{e}")
      if response.status != 200:
        if response.status == 503:
          await matcher.finish("访问过于频繁，请稍后再试")
        else:
          await matcher.finish(f"HTTP错误: {response.status}")
      posts = get_by_path(await response.json(), site.array_path)
      if len(posts) == 0:
        await matcher.send("没有结果")
        return
      segments = []
      for post in posts:
        url = POST_URL.format(id=get_by_path(post, site.id_path))
        segments.append(url)
        try:
          response = await http.get(get_by_path(post, site.sample_path), proxy=definition.proxy)
          segments.append(f"[CQ:image,file=base64://{base64.b64encode(await response.read())}]")
        except aiohttp.ClientError:
          segments.append("预览下载失败")
    await matcher.send(Message("\n".join(segments)))
  site = definition.to_site()
  HEADERS = {"User-Agent": definition.user_agent}
  POST_URL = site.origin + site.post_url
  API_URL = site.origin + site.api_url
  parser = ArgumentParser(add_help=False)
  parser.add_argument("tags", nargs="+", metavar="标签")
  parser.add_argument(
    "-limit", type=int, default=CONFIG.default_limit, metavar="图片数",
    help=f"每页的图片数，默认为{CONFIG.default_limit}，不能超过{CONFIG.max_limit}")
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


for site in CONFIG.sites:
  register(site)
