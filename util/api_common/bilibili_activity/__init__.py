import json
from dataclasses import dataclass
from typing import (
  TYPE_CHECKING, Any, Dict, Generic, Iterable, List, Literal, Optional, Protocol, Sequence, Tuple,
  Type, TypeVar, Union, cast, overload,
)
from urllib.parse import urlparse

from util import misc
from .. import bilibili_auth

try:
  import grpc.aio

  from .protos.bilibili.app.dynamic.v2.dynamic_pb2 import (
    AddButtonType, AdditionalType, Description, DescType, DisableState, DynamicItem, DynamicType,
    DynDetailReq, DynDetailsReq, DynModuleType, DynSpaceReq, ModuleAdditional, VideoSubType,
  )
  from .protos.bilibili.app.dynamic.v2.dynamic_pb2_grpc import DynamicStub
except ImportError:
  GRPC_AVAILABLE = False
else:
  GRPC_AVAILABLE = True


if TYPE_CHECKING:
  import grpc.aio

  from .protos.bilibili.app.dynamic.v2.dynamic_pb2 import (
    AddButtonType, AdditionalType, DescType, DisableState, DynamicType, DynDetailReq,
    DynDetailsReq, DynModuleType, DynSpaceReq, Module, VideoSubType,
  )
  from .protos.bilibili.app.dynamic.v2.dynamic_pb2_grpc import (
    DynamicAsyncStub, DynamicStub,
  )

Modules = Dict["DynModuleType.V", "Module"]
TContent = TypeVar("TContent", covariant=True)
TExtra = TypeVar("TExtra", covariant=True)

LIST_API = "https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space" \
  "?host_mid={uid}&offset={offset}"
DETAIL_API = "https://api.bilibili.com/x/polymer/web-dynamic/v1/detail" \
  "?id={id}"
LIST_API_OLD = "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/space_history" \
  "?host_uid={uid}&offset_dynamic_id={offset}"
DETAIL_API_OLD = "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/get_dynamic_detail" \
  "?dynamic_id={id}"
GRPC_API = "grpc.biliapi.net"
GRPC_METADATA = (
  ('x-bili-device-bin', b'\x10\x80\xe7\x8f\x03\x1a%XY5ADF45C6BF3BD3FAE8126774BD8E4E7DFC5"\x07android*\x07android2\x05phone:\x04bili'),  # noqa: E501
  ('x-bili-local-bin', b''),
  ('x-bili-metadata-bin', b'\x12\x07android\x1a\x05phone \x80\xe7\x8f\x03*\x04bili2%XY5ADF45C6BF3BD3FAE8126774BD8E4E7DFC5:\x07android'),  # noqa: E501
  ('x-bili-network-bin', b'\x08\x01'),
)


async def grpc_fetch(uid: int, offset: str = "") -> Tuple[Sequence["DynamicItem"], Optional[str]]:
  async with grpc.aio.secure_channel(GRPC_API, grpc.ssl_channel_credentials()) as channel:
    stub = cast("DynamicAsyncStub", DynamicStub(channel))
    req = DynSpaceReq(host_uid=uid, history_offset=offset)
    res = await stub.DynSpace(req)
  next_offset = res.history_offset if res.has_more else None
  return res.list, next_offset


async def json_fetch(uid: int, offset: str = "") -> Tuple[List[Dict[Any, Any]], Optional[str]]:
  http = misc.http()
  headers = {
    "Cookie": bilibili_auth.get_cookie(),
    "User-Agent": misc.BROWSER_UA,
  }
  async with http.get(LIST_API.format(uid=uid, offset=offset), headers=headers) as response:
    data = await response.json()
  next_offset = data["data"]["offset"] if data["data"]["has_more"] else None
  return data["data"]["items"], next_offset


@overload
async def grpc_get(id: str) -> "DynamicItem": ...
@overload
async def grpc_get(id: List[str]) -> List["DynamicItem"]: ...
async def grpc_get(id: Union[str, List[str]]) -> Union["DynamicItem", List["DynamicItem"]]:
  async with grpc.aio.secure_channel(GRPC_API, grpc.ssl_channel_credentials()) as channel:
    stub = cast("DynamicAsyncStub", DynamicStub(channel))
    if isinstance(id, list):
      req = DynDetailsReq(dynamic_ids=",".join(id))
      res = await stub.DynDetails(req, metadata=GRPC_METADATA)
      return list(res.list)
    req2 = DynDetailReq(dynamic_id=id)
    res2 = await stub.DynDetail(req2, metadata=GRPC_METADATA)
    return res2.item


async def json_get(id: str, cookie: str = "") -> Dict[Any, Any]:
  http = misc.http()
  headers = {
    "Referer": f"https://t.bilibili.com/{id}",
    "Cookie": bilibili_auth.get_cookie(),
    "User-Agent": misc.BROWSER_UA,
  }
  async with http.get(DETAIL_API.format(id=id), headers=headers) as response:
    data = await response.json()
  return data["data"]["item"]


@dataclass
class RichTextEmotion:
  url: str


@dataclass
class RichTextLink:
  text: str


RichTextNode = Union[str, RichTextEmotion, RichTextLink]
RichText = List[RichTextNode]


def grpc_parse_richtext(desc: Iterable["Description"]) -> RichText:
  nodes: RichText = []
  for node in desc:
    if node.type == DescType.desc_type_text:
      nodes.append(node.text)
    elif node.type == DescType.desc_type_emoji:
      nodes.append(RichTextEmotion(node.uri))
    else:
      nodes.append(RichTextLink(node.text))
  return nodes


def json_parse_richtext(text: List[Dict[Any, Any]]) -> RichText:
  nodes: RichText = []
  for node in text:
    if node["type"] == "RICH_TEXT_NODE_TYPE_TEXT":
      nodes.append(node["text"])
    elif node["type"] == "RICH_TEXT_NODE_TYPE_EMOJI":
      nodes.append(RichTextEmotion(node["emoji"]["icon_url"]))
    else:
      nodes.append(RichTextLink(node["text"]))
  return nodes


class ContentParser(Protocol[TContent]):
  @staticmethod
  def grpc_parse(item: "DynamicItem", modules: Modules) -> TContent:
    raise NotImplementedError

  @staticmethod
  def json_parse(item: Dict[Any, Any]) -> TContent:
    raise NotImplementedError


@dataclass
class ContentText(ContentParser["ContentText"]):
  text: str
  richtext: RichText

  @staticmethod
  def grpc_parse(item: "DynamicItem", modules: Modules) -> "ContentText":
    desc = modules[DynModuleType.module_desc].module_desc
    return ContentText(desc.text, grpc_parse_richtext(desc.desc))

  @staticmethod
  def json_parse(item: Dict[Any, Any]) -> "ContentText":
    desc = item["modules"]["module_dynamic"]["desc"]
    return ContentText(desc["text"], json_parse_richtext(desc["rich_text_nodes"]))


@dataclass
class Image:
  src: str
  width: int
  height: int
  size: float


@dataclass
class ContentImage(ContentParser["ContentImage"]):
  text: str
  richtext: RichText
  images: List[Image]

  @staticmethod
  def grpc_parse(item: "DynamicItem", modules: Modules) -> "ContentImage":
    desc = modules[DynModuleType.module_desc].module_desc
    return ContentImage(
      desc.text,
      grpc_parse_richtext(desc.desc),
      [Image(
        image.src,
        image.width,
        image.height,
        image.size,
      ) for image in modules[DynModuleType.module_dynamic].module_dynamic.dyn_draw.items],
    )

  @staticmethod
  def json_parse(item: Dict[Any, Any]) -> "ContentImage":
    module = item["modules"]["module_dynamic"]
    desc = module["desc"]
    return ContentImage(
      desc["text"],
      json_parse_richtext(desc["rich_text_nodes"]),
      [Image(
        image["src"],
        image["width"],
        image["height"],
        image["size"],
      ) for image in module["major"]["draw"]["items"]],
    )


@dataclass
class ContentVideo(ContentParser["ContentVideo"]):
  text: str
  richtext: RichText  # 动态视频有富文本
  avid: int
  bvid: str
  title: str
  desc: Optional[str]
  cover: str
  view: Optional[int]
  duration: int
  width: Optional[int]
  height: Optional[int]
  formatted_view: str
  formatted_danmaku: str

  @staticmethod
  def grpc_parse(item: "DynamicItem", modules: Modules) -> "ContentVideo":
    video = modules[DynModuleType.module_dynamic].module_dynamic.dyn_archive
    if DynModuleType.module_desc in modules:
      desc_module = modules[DynModuleType.module_desc].module_desc
      text = desc_module.text
      richtext = grpc_parse_richtext(desc_module.desc)
    else:
      text = ""
      richtext = []
    return ContentVideo(
      text,
      richtext,
      video.avid,
      video.bvid,
      video.title,
      None,
      video.cover,
      video.view,
      video.duration,
      video.dimension.width,
      video.dimension.height,
      misc.removesuffix(video.cover_left_text_2, "观看"),
      misc.removesuffix(video.cover_left_text_3, "弹幕"),
    )

  @staticmethod
  def json_parse(item: Dict[Any, Any]) -> "ContentVideo":
    module = item["modules"]["module_dynamic"]
    video = module["major"]["archive"]
    duration_text: str = video["duration_text"]
    try:
      duration_seg = duration_text.split(":")
      if len(duration_seg) == 2:
        h = 0
        m, s = duration_seg
      else:
        h, m, s = duration_seg
      duration = int(h) * 3600 + int(m) * 60 + int(s)
    except ValueError:
      duration = -1
    desc = module["desc"]
    if desc:
      text = desc["text"]
      richtext = json_parse_richtext(desc["rich_text_nodes"])
    else:
      text = ""
      richtext = []
    return ContentVideo(
      text,
      richtext,
      video["aid"],
      video["bvid"],
      video["title"],
      video["desc"],
      video["cover"],
      None,
      duration,
      None,
      None,
      video["stat"]["play"],
      video["stat"]["danmaku"],
    )


@dataclass
class ContentArticle(ContentParser["ContentArticle"]):
  '''
  专栏
  https://www.bilibili.com/read/cv<ID>
  '''
  id: int
  title: str
  desc: str
  covers: List[str]
  formatted_view: str

  @staticmethod
  def grpc_parse(item: "DynamicItem", modules: Modules) -> "ContentArticle":
    article = modules[DynModuleType.module_dynamic].module_dynamic.dyn_article
    return ContentArticle(
      int(item.extend.business_id),
      article.title,
      article.desc,
      list(article.covers),
      article.label,
    )

  @staticmethod
  def json_parse(item: Dict[Any, Any]) -> "ContentArticle":
    major = item["modules"]["module_dynamic"]["major"]["article"]
    return ContentArticle(
      major["id"],
      major["title"],
      major["desc"],
      major["covers"],
      major["label"],
    )


@dataclass
class ContentAudio(ContentParser["ContentAudio"]):
  '''
  音频
  https://www.bilibili.com/audio/au<ID>
  '''
  id: int
  title: str
  desc: Optional[str]
  cover: str
  label: str

  @staticmethod
  def grpc_parse(item: "DynamicItem", modules: Modules) -> "ContentAudio":
    audio = modules[DynModuleType.module_dynamic].module_dynamic.dyn_music
    return ContentAudio(
      audio.id,
      audio.title,
      None,
      audio.cover,
      audio.label1,
    )

  @staticmethod
  def json_parse(item: Dict[Any, Any]) -> "ContentAudio":
    module = item["modules"]["module_dynamic"]
    audio = module["major"]["music"]
    return ContentAudio(
      audio["id"],
      audio["title"],
      module["desc"]["text"],
      audio["cover"],
      audio["label"],
    )


@dataclass
class ContentPGC(ContentParser["ContentPGC"]):
  '''
  番剧、电视剧、电影、纪录片等 PGC（Professional Generated Content，专业生产内容，与之相对的是
  User Generated Content，用户生产内容，就是 UP 主上传的视频、专栏等）
  https://www.bilibili.com/bangumi/media/md<SSID> # 介绍页
  https://www.bilibili.com/bangumi/play/ss<SSID> # 播放第一集
  https://www.bilibili.com/bangumi/play/ep<EPID> # 播放指定集
  这种动态只会出现在转发里
  '''
  ssid: int
  epid: int
  season_name: str
  episode_name: str
  season_cover: Optional[str]
  episode_cover: str
  label: Optional[str]
  formatted_view: str
  formatted_danmaku: str
  duration: Optional[int]
  width: Optional[int]
  height: Optional[int]

  @staticmethod
  def grpc_parse(item: "DynamicItem", modules: Modules) -> "ContentPGC":
    pgc = modules[DynModuleType.module_dynamic].module_dynamic.dyn_pgc
    subtypes = {
      VideoSubType.VideoSubTypeBangumi: "番剧",
      VideoSubType.VideoSubTypeMovie: "电影",
      VideoSubType.VideoSubTypeDocumentary: "纪录片",
      VideoSubType.VideoSubTypeDomestic: "国创",
      VideoSubType.VideoSubTypeTeleplay: "电视剧",
    }

    return ContentPGC(
      pgc.season_id,
      pgc.epid,
      pgc.season.title,
      pgc.title,
      None,
      pgc.cover,
      subtypes.get(pgc.sub_type),
      pgc.cover_left_text_2,
      pgc.cover_left_text_3,
      pgc.duration,
      pgc.dimension.width,
      pgc.dimension.height,
    )

  @staticmethod
  def json_parse(item: Dict[Any, Any]) -> "ContentPGC":
    author = item["modules"]["module_author"]
    pgc = item["modules"]["module_dynamic"]["major"]["pgc"]
    return ContentPGC(
      pgc["season_id"],
      pgc["epid"],
      author["name"],
      pgc["title"],
      author["face"],
      pgc["cover"],
      author["label"],
      pgc["stat"]["play"],
      pgc["stat"]["danmaku"],
      None,
      None,
      None,
    )


@dataclass
class ContentCommon(ContentParser["ContentCommon"]):
  '''通用方卡（用于番剧评分、大会员活动等）和通用竖卡（暂时不明）'''
  text: str
  richtext: RichText
  cover: str
  title: str
  desc: str
  badge: str
  vertical: bool

  @staticmethod
  def grpc_parse(item: "DynamicItem", modules: Modules) -> "ContentCommon":
    desc = modules[DynModuleType.module_desc].module_desc
    common = modules[DynModuleType.module_dynamic].module_dynamic.dyn_common
    return ContentCommon(
      desc.text,
      grpc_parse_richtext(desc.desc),
      common.cover,
      common.title,
      common.desc,
      common.badge[0].text if common.badge else "",
      item.item_type == DynamicType.common_vertical,
    )

  @staticmethod
  def json_parse(item: Dict[Any, Any]) -> "ContentCommon":
    module = item["modules"]["module_dynamic"]
    common = module["major"]["common"]
    desc = module["desc"]
    return ContentCommon(
      desc["text"],
      json_parse_richtext(desc["rich_text_nodes"]),
      common["cover"],
      common["title"],
      common["desc"],
      common["badge"]["text"],
      item["type"] == "DYNAMIC_TYPE_COMMON_VERTICAL",
    )


@dataclass
class ContentLive(ContentParser["ContentLive"]):
  '''
  直播间
  这种动态只会出现在转发里
  '''
  id: int
  title: str
  category: str
  cover: str
  streaming: bool

  @staticmethod
  def grpc_parse(item: "DynamicItem", modules: Modules) -> "ContentLive":
    live = modules[DynModuleType.module_dynamic].module_dynamic.dyn_common_live
    return ContentLive(
      live.id,
      live.title,
      live.cover_label,
      live.cover,
      live.badge.text != "直播结束",
    )

  @staticmethod
  def json_parse(item: Dict[Any, Any]) -> "ContentLive":
    live = item["modules"]["module_dynamic"]["major"]["live"]
    return ContentLive(
      live["id"],
      live["title"],
      live["desc_first"],
      live["cover"],
      bool(live["live_state"]),
    )


@dataclass
class ContentLiveRcmd(ContentParser["ContentLiveRcmd"]):
  '''
  直播推荐/直播场次
  这种动态可能出现在转发里，也可能出现在动态里
  下播之后对应动态也会消失
  '''
  live_id: int
  room_id: int
  uid: int
  title: str
  cover: str
  category: str
  category_id: int
  parent_category: str
  parent_category_id: int
  start_time: int
  watching: int

  @staticmethod
  def grpc_parse(item: "DynamicItem", modules: Modules) -> "ContentLiveRcmd":
    live = json.loads(modules[DynModuleType.module_dynamic].module_dynamic.dyn_live_rcmd.content)
    live = live["live_play_info"]
    return ContentLiveRcmd(
      int(live["live_id"]),
      live["room_id"],
      live["uid"],
      live["title"],
      live["cover"],
      live["area_name"],
      live["area_id"],
      live["parent_area_name"],
      live["parent_area_id"],
      live["live_start_time"],
      live["watched_show"]["num"],
    )

  @staticmethod
  def json_parse(item: Dict[Any, Any]) -> "ContentLiveRcmd":
    live = json.loads(item["modules"]["module_dynamic"]["major"]["live_rcmd"]["content"])
    live = live["live_play_info"]
    return ContentLiveRcmd(
      int(live["live_id"]),
      live["room_id"],
      live["uid"],
      live["title"],
      live["cover"],
      live["area_name"],
      live["area_id"],
      live["parent_area_name"],
      live["parent_area_id"],
      live["live_start_time"],
      live["watched_show"]["num"],
    )


@dataclass
class ContentCourse(ContentParser["ContentCourse"]):
  '''
  课程
  这种动态只会出现在转发里
  '''
  id: int
  title: str
  desc: str
  stat: str
  cover: str

  @staticmethod
  def grpc_parse(item: "DynamicItem", modules: Modules) -> "ContentCourse":
    course = modules[DynModuleType.module_dynamic].module_dynamic.dyn_cour_season
    return ContentCourse(
      int(item.extend.business_id),
      course.title,
      course.desc,
      course.text_1,
      course.cover,
    )

  @staticmethod
  def json_parse(item: Dict[Any, Any]) -> "ContentCourse":
    course = item["modules"]["module_dynamic"]["major"]["courses"]
    return ContentCourse(
      course["id"],
      course["title"],
      course["sub_title"],
      course["desc"],
      course["cover"],
    )


@dataclass
class ContentPlaylist(ContentParser["ContentPlaylist"]):
  '''
  合集（播放列表）
  这种动态只会出现在转发里
  '''
  id: int
  title: str
  stat: str
  cover: str

  @staticmethod
  def grpc_parse(item: "DynamicItem", modules: Modules) -> "ContentPlaylist":
    medialist = modules[DynModuleType.module_dynamic].module_dynamic.dyn_medialist
    return ContentPlaylist(
      medialist.id,
      medialist.title,
      medialist.sub_title,
      medialist.cover,
    )

  # JSON API 获取不到转发合集，所以只有 grpc_parse
  @staticmethod
  def json_parse(item: Dict[Any, Any]) -> "ContentPlaylist":
    raise NotImplementedError


@dataclass
class ContentForward(ContentParser["ContentForward"]):
  text: str
  richtext: RichText
  activity: Optional["Activity[object, object]"]
  error_text: str

  @staticmethod
  def grpc_parse(item: "DynamicItem", modules: Modules) -> "ContentForward":
    if DynModuleType.module_dynamic in modules:
      original = Activity.grpc_parse(
        modules[DynModuleType.module_dynamic].module_dynamic.dyn_forward.item,
      )
      error_text = ""
    else:
      original = None  # 源动态失效
      error_text = modules[DynModuleType.module_item_null].module_item_null.text
    desc = modules[DynModuleType.module_desc].module_desc
    return ContentForward(
      desc.text,
      grpc_parse_richtext(desc.desc),
      original,
      error_text,
    )

  @staticmethod
  def json_parse(item: Dict[Any, Any]) -> "ContentForward":
    if item["orig"]["type"] == "DYNAMIC_TYPE_NONE":
      original = None  # 源动态失效
      error_text = item["orig"]["modules"]["module_dynamic"]["major"]["none"]["tips"]
    else:
      original = Activity.json_parse(item["orig"])
      error_text = ""
    desc = item["modules"]["module_dynamic"]["desc"]
    return ContentForward(
      desc["text"],
      json_parse_richtext(desc["rich_text_nodes"]),
      original,
      error_text,
    )


class ContentUnknown(ContentParser["ContentUnknown"]):
  @staticmethod
  def grpc_parse(item: "DynamicItem", modules: Modules) -> "ContentUnknown":
    return ContentUnknown()

  @staticmethod
  def json_parse(item: Dict[Any, Any]) -> "ContentUnknown":
    return ContentUnknown()


GRPC_CONTENT_TYPES: Dict["DynamicType.V", Type[ContentParser[object]]] = {
  DynamicType.word: ContentText,
  DynamicType.draw: ContentImage,
  DynamicType.av: ContentVideo,
  DynamicType.article: ContentArticle,
  DynamicType.music: ContentAudio,
  DynamicType.pgc: ContentPGC,
  DynamicType.common_square: ContentCommon,
  DynamicType.common_vertical: ContentCommon,
  DynamicType.courses_season: ContentCourse,
  DynamicType.live: ContentLive,
  DynamicType.live_rcmd: ContentLiveRcmd,
  DynamicType.medialist: ContentPlaylist,
  DynamicType.forward: ContentForward,
} if GRPC_AVAILABLE else {}
JSON_CONTENT_TYPES: Dict[str, Type[ContentParser[object]]] = {
  "WORD": ContentText,
  "DRAW": ContentImage,
  "AV": ContentVideo,
  "ARTICLE": ContentArticle,
  "MUSIC": ContentAudio,
  "PGC": ContentPGC,
  "COMMON_SQUARE": ContentCommon,
  "COMMON_VERTICAL": ContentCommon,
  "COURSES_SEASON": ContentCourse,
  "LIVE": ContentLive,
  "LIVE_RCMD": ContentLiveRcmd,
  # JSON API 获取不到转发合集
  "FORWARD": ContentForward,
}


class ExtraParser(Protocol[TExtra]):
  @staticmethod
  def grpc_parse(item: "ModuleAdditional") -> TExtra:
    raise NotImplementedError

  @staticmethod
  def json_parse(item: Dict[Any, Any]) -> TExtra:
    raise NotImplementedError


@dataclass
class ExtraVote(ExtraParser["ExtraVote"]):
  id: int
  uid: int
  title: str
  count: int
  end: int

  @staticmethod
  def grpc_parse(item: "ModuleAdditional") -> "ExtraVote":
    return ExtraVote(
      item.vote2.vote_id,
      0,
      item.vote2.title,
      item.vote2.total,
      item.vote2.deadline,
    )

  @staticmethod
  def json_parse(item: Dict[Any, Any]) -> "ExtraVote":
    return ExtraVote(
      item["vote"]["vote_id"],
      item["vote"]["uid"],
      item["vote"]["desc"],
      item["vote"]["join_num"] or 0,  # 0 人时是 null
      item["vote"]["end_time"],
    )


@dataclass
class ExtraVideo(ExtraParser["ExtraVideo"]):
  id: int
  title: str
  desc: str
  duration: str
  cover: str

  @staticmethod
  def grpc_parse(item: "ModuleAdditional") -> "ExtraVideo":
    uri = urlparse(item.ugc.uri)
    return ExtraVideo(
      int(uri.path[1:]),
      item.ugc.title,
      item.ugc.desc_text_2,
      item.ugc.duration,
      item.ugc.cover,
    )

  @staticmethod
  def json_parse(item: Dict[Any, Any]) -> "ExtraVideo":
    return ExtraVideo(
      int(item["ugc"]["id_str"]),
      item["ugc"]["title"],
      item["ugc"]["desc_second"],
      item["ugc"]["duration"],
      item["ugc"]["cover"],
    )


@dataclass
class ExtraReserve(ExtraParser["ExtraReserve"]):
  id: int
  uid: int
  title: str
  desc: str
  desc2: str
  count: int
  link_text: str
  link_url: str
  type: Literal["video", "live"]
  status: Literal["reserving", "streaming", "expired"]
  content_url: str

  @staticmethod
  def grpc_parse(item: "ModuleAdditional") -> "ExtraReserve":
    type = "live" if "直播" in item.up.desc_text_1.text else "video"
    if type == "live":
      if item.up.button.type == AddButtonType.bt_jump:
        status = "streaming"
      else:
        status = "expired" if item.up.button.check.disable == DisableState.gary else "reserving"
    else:
      status = "expired" if item.up.button.type == AddButtonType.bt_jump else "reserving"
    return ExtraReserve(
      item.rid,
      item.up.up_mid,
      item.up.title,
      item.up.desc_text_1.text,
      item.up.desc_text_2,
      item.up.reserve_total,
      item.up.desc_text3.text,
      item.up.desc_text3.jump_url,
      type,
      status,
      item.up.url,
    )

  @staticmethod
  def json_parse(item: Dict[Any, Any]) -> "ExtraReserve":
    type = "video" if item["reserve"]["stype"] == 1 else "live"
    if type == "live":
      if item["reserve"]["button"]["type"] == 1:
        status = "streaming"
      else:
        status = "expired" if "disable" in item["reserve"]["button"]["uncheck"] else "reserving"
    else:
      status = "expired" if item["reserve"]["button"]["type"] == 1 else "reserving"
    return ExtraReserve(
      item["reserve"]["rid"],
      item["reserve"]["up_mid"],
      item["reserve"]["title"],
      item["reserve"]["desc1"]["text"],
      item["reserve"]["desc2"]["text"],
      item["reserve"]["reserve_total"],
      item["reserve"]["desc3"]["text"],
      item["reserve"]["desc3"]["jump_url"],
      type,
      status,
      item["reserve"]["jump_url"],
    )


@dataclass
class Goods:
  id: int
  name: str
  price: str
  url: str
  image: str


@dataclass
class ExtraGoods(ExtraParser["ExtraGoods"]):
  title: str
  goods: List[Goods]

  @staticmethod
  def grpc_parse(item: "ModuleAdditional") -> "ExtraGoods":
    goods = [
      Goods(i.item_id, i.title, i.price, i.jump_url, i.cover) for i in item.goods.goods_items
    ]
    return ExtraGoods(item.goods.rcmd_desc, goods)

  @staticmethod
  def json_parse(item: Dict[Any, Any]) -> "ExtraGoods":
    goods = [
      Goods(int(i["id"]), i["name"], i["price"], i["url"], i["cover"])
      for i in item["goods"]["items"]
    ]
    return ExtraGoods(item["goods"]["head_text"], goods)


class ExtraUnknown(ExtraParser["ExtraUnknown"]):
  @staticmethod
  def grpc_parse(item: "ModuleAdditional") -> "ExtraUnknown":
    return ExtraUnknown()

  @staticmethod
  def json_parse(item: Dict[Any, Any]) -> "ExtraUnknown":
    return ExtraUnknown()


GRPC_EXTRA_TYPES: Dict["AdditionalType.V", Type[ExtraParser[object]]] = {
  AdditionalType.additional_type_vote: ExtraVote,
  AdditionalType.additional_type_ugc: ExtraVideo,
  AdditionalType.additional_type_up_reservation: ExtraReserve,
  AdditionalType.additional_type_goods: ExtraGoods,
} if GRPC_AVAILABLE else {}
JSON_EXTRA_TYPES: Dict[str, Type[ExtraParser[object]]] = {
  "VOTE": ExtraVote,
  "UGC": ExtraVideo,
  "RESERVE": ExtraReserve,
  "GOODS": ExtraGoods,
}


@dataclass
class Stat:
  repost: int
  like: int
  reply: int


@dataclass
class Extra(Generic[TExtra]):
  type: str
  value: TExtra


@dataclass
class Topic:
  id: int
  name: str


@dataclass
class Activity(Generic[TContent, TExtra]):
  uid: int
  name: str
  avatar: str
  id: str
  top: bool
  type: str
  content: TContent
  stat: Optional[Stat]
  time: Optional[int]
  extra: Optional[Extra[TExtra]]
  topic: Optional[Topic]

  @staticmethod
  def grpc_parse(item: "DynamicItem") -> "Activity[object, object]":
    modules = {module.module_type: module for module in item.modules}
    if DynModuleType.module_author_forward in modules:
      author_module = modules[DynModuleType.module_author_forward].module_author_forward
      uid = author_module.uid
      name = misc.removeprefix(author_module.title[0].text, "@")
      avatar = author_module.face_url
      top = False
    else:
      author_module = modules[DynModuleType.module_author].module_author
      uid = author_module.author.mid
      name = author_module.author.name
      avatar = author_module.author.face
      top = author_module.is_top
    if DynModuleType.module_bottom in modules:
      # buttom 的 u 是 B 站拼错了，不是我（甩锅）
      stat_module = modules[DynModuleType.module_bottom].module_buttom.module_stat
    elif DynModuleType.module_stat_forward in modules:
      stat_module = modules[DynModuleType.module_stat_forward].module_stat_forward
    else:
      stat_module = modules[DynModuleType.module_stat].module_stat
    content_cls = GRPC_CONTENT_TYPES.get(item.card_type, ContentUnknown)
    extra = None
    if DynModuleType.module_additional in modules:
      additional_module = modules[DynModuleType.module_additional].module_additional
      extra = Extra(
        misc.removeprefix(AdditionalType.Name(additional_module.type).upper(), "ADDITIONAL_TYPE_"),
        GRPC_EXTRA_TYPES.get(additional_module.type, ExtraUnknown).grpc_parse(additional_module),
      )
    topic = None
    if DynModuleType.module_topic in modules:
      topic_module = modules[DynModuleType.module_topic].module_topic
      topic = Topic(topic_module.id, topic_module.name)
    return Activity(
      uid,
      name,
      avatar,
      item.extend.dyn_id_str,
      top,
      misc.removeprefix(DynamicType.Name(item.card_type).upper(), "DYN_"),
      content_cls.grpc_parse(item, modules),
      Stat(stat_module.like, stat_module.repost, stat_module.reply),
      None,
      extra,
      topic,
    )

  @staticmethod
  def json_parse(item: Dict[Any, Any]) -> "Activity[object, object]":
    modules = item["modules"]
    author_module = modules["module_author"]
    top = "module_tag" in modules and modules["module_tag"]["text"] == "置顶"
    stat = None
    if "module_stat" in modules:
      stat_module = modules["module_stat"]
      stat = Stat(
        stat_module["forward"]["count"],
        stat_module["like"]["count"],
        stat_module["comment"]["count"],
      )
    type = item["type"].removeprefix("DYNAMIC_TYPE_")
    content_cls = JSON_CONTENT_TYPES.get(type, ContentUnknown)
    dynamic_module = modules["module_dynamic"]
    extra = None
    if (additional := dynamic_module["additional"]) is not None:
      extra_type = additional["type"].removeprefix("ADDITIONAL_TYPE_")
      extra_cls = JSON_EXTRA_TYPES.get(extra_type, ExtraUnknown)
      extra = Extra(extra_type, extra_cls.json_parse(additional))
    topic = None
    if (raw_topic := dynamic_module["topic"]) is not None:
      topic = Topic(raw_topic["id"], raw_topic["name"])
    return Activity(
      author_module["mid"],
      author_module["name"],
      author_module["face"],
      item["id_str"],
      top,
      type,
      content_cls.json_parse(item),
      stat,
      author_module["pub_ts"],
      extra,
      topic,
    )

ActivityText = Activity[ContentText, TExtra]
ActivityImage = Activity[ContentImage, TExtra]
ActivityArticle = Activity[ContentArticle, TExtra]
ActivityVideo = Activity[ContentVideo, TExtra]
ActivityAudio = Activity[ContentAudio, TExtra]
ActivityPGC = Activity[ContentPGC, TExtra]
ActivityCommonSquare = Activity[ContentCommon, TExtra]
ActivityForward = Activity[ContentForward, TExtra]
ActivityLive = Activity[ContentLive, TExtra]
ActivityLiveRcmd = Activity[ContentLiveRcmd, TExtra]
ActivityCourse = Activity[ContentCourse, TExtra]
ActivityPlaylist = Activity[ContentPlaylist, TExtra]
