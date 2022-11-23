import asyncio
import calendar
import json
import re
from datetime import date, datetime, time, timedelta
from io import BytesIO
from typing import Any, List, Optional, Tuple

import nonebot
import wordcloud
from jieba.analyse import TFIDF
from loguru import logger
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent, MessageSegment
from nonebot.params import CommandArg
from PIL import Image
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import desc, func, select

from util import command, configs, context, imutil, misc, record


class Config(BaseModel):
  font: Optional[str] = None
  width: int = 400
  height: int = 200
  bg: int = 0xffffff
  # https://matplotlib.org/stable/tutorials/colors/colormaps.html
  fg: str = "viridis"
  limit: int = 10000
  idf_path: str = ""
  stopwords_path: str = ""
  leaderboard_linit: int = 10

CONFIG = configs.SharedConfig("wordcloud", Config)
USAGE = '''\
/{} [开始日期 [结束日期]]
范围包含开始日期和结束日期，开始日期不填默认为今天，结束日期不填默认与开始日期相同
日期可以是以下格式
完整：2022-1-1、2022/1/1、2022年1月1日、20220101
年月：2022-1、2022/1、2022年1月、202201
月日：1-1、1/1、1月1日
年份：2022、2022年
月份：1月
日期：1日
短语：今天、昨天、本周、上周、本月、上月、今年、去年'''

CHINESE_Y_RE = re.compile(r"^(\d{2}|\d{4})年?$")
CHINESE_M_RE = re.compile(r"^(\d{1,2})月$")
CHINESE_D_RE = re.compile(r"^(\d{1,2})[日号]$")
CHINESE_YM_RE = re.compile(r"^(\d{2}|\d{4})年(\d{1,2})月?$")
CHINESE_MD_RE = re.compile(r"^(\d{1,2})月(\d{1,2})[日号]??$")
CHINESE_YMD_RE = re.compile(r"^(\d{2}|\d{4})年(\d{1,2})月(\d{1,2})[日号]?$")
DASH_YM_RE = re.compile(r"^(\d{2}|\d{4})-(\d{1,2})$")
DASH_MD_RE = re.compile(r"^(\d{1,2})-(\d{1,2})$")
DASH_YMD_RE = re.compile(r"^(\d{2}|\d{4})-(\d{1,2})-(\d{1,2})$")
SLASH_YM_RE = re.compile(r"^(\d{2}|\d{4})/\d{1,2}$")
SLASH_MD_RE = re.compile(r"^(\d{1,2})/(\d{1,2})$")
SLASH_YMD_RE = re.compile(r"^(\d{2}|\d{4})/(\d{1,2})/(\d{1,2})$")

# https://github.com/he0119/nonebot-plugin-wordcloud/blob/main/nonebot_plugin_wordcloud/data_source.py#L18
# 这个又是从 https://stackoverflow.com/a/17773849/9212748 搬的
# 二道贩子（雾）
URL_RE = re.compile(r"(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|www\.[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,}|www\.[a-zA-Z0-9]+\.[^\s]{2,})")  # noqa
# https://github.com/mathiasbynens/emoji-regex
EMOJI_RE = re.compile(r"(?:[#*0-9]\uFE0F?\u20E3|[\xA9\xAE\u203C\u2049\u2122\u2139\u2194-\u2199\u21A9\u21AA\u231A\u231B\u2328\u23CF\u23ED-\u23EF\u23F1\u23F2\u23F8-\u23FA\u24C2\u25AA\u25AB\u25B6\u25C0\u25FB\u25FC\u25FE\u2600-\u2604\u260E\u2611\u2614\u2615\u2618\u2620\u2622\u2623\u2626\u262A\u262E\u262F\u2638-\u263A\u2640\u2642\u2648-\u2653\u265F\u2660\u2663\u2665\u2666\u2668\u267B\u267E\u267F\u2692\u2694-\u2697\u2699\u269B\u269C\u26A0\u26A7\u26AA\u26B0\u26B1\u26BD\u26BE\u26C4\u26C8\u26CF\u26D1\u26D3\u26E9\u26F0-\u26F5\u26F7\u26F8\u26FA\u2702\u2708\u2709\u270F\u2712\u2714\u2716\u271D\u2721\u2733\u2734\u2744\u2747\u2757\u2763\u27A1\u2934\u2935\u2B05-\u2B07\u2B1B\u2B1C\u2B55\u3030\u303D\u3297\u3299]\uFE0F?|[\u261D\u270C\u270D](?:\uFE0F|\uD83C[\uDFFB-\uDFFF])?|[\u270A\u270B](?:\uD83C[\uDFFB-\uDFFF])?|[\u23E9-\u23EC\u23F0\u23F3\u25FD\u2693\u26A1\u26AB\u26C5\u26CE\u26D4\u26EA\u26FD\u2705\u2728\u274C\u274E\u2753-\u2755\u2795-\u2797\u27B0\u27BF\u2B50]|\u26F9(?:\uFE0F|\uD83C[\uDFFB-\uDFFF])?(?:\u200D[\u2640\u2642]\uFE0F?)?|\u2764\uFE0F?(?:\u200D(?:\uD83D\uDD25|\uD83E\uDE79))?|\uD83C(?:[\uDC04\uDD70\uDD71\uDD7E\uDD7F\uDE02\uDE37\uDF21\uDF24-\uDF2C\uDF36\uDF7D\uDF96\uDF97\uDF99-\uDF9B\uDF9E\uDF9F\uDFCD\uDFCE\uDFD4-\uDFDF\uDFF5\uDFF7]\uFE0F?|[\uDF85\uDFC2\uDFC7](?:\uD83C[\uDFFB-\uDFFF])?|[\uDFC3\uDFC4\uDFCA](?:\uD83C[\uDFFB-\uDFFF])?(?:\u200D[\u2640\u2642]\uFE0F?)?|[\uDFCB\uDFCC](?:\uFE0F|\uD83C[\uDFFB-\uDFFF])?(?:\u200D[\u2640\u2642]\uFE0F?)?|[\uDCCF\uDD8E\uDD91-\uDD9A\uDE01\uDE1A\uDE2F\uDE32-\uDE36\uDE38-\uDE3A\uDE50\uDE51\uDF00-\uDF20\uDF2D-\uDF35\uDF37-\uDF7C\uDF7E-\uDF84\uDF86-\uDF93\uDFA0-\uDFC1\uDFC5\uDFC6\uDFC8\uDFC9\uDFCF-\uDFD3\uDFE0-\uDFF0\uDFF8-\uDFFF]|\uDDE6\uD83C[\uDDE8-\uDDEC\uDDEE\uDDF1\uDDF2\uDDF4\uDDF6-\uDDFA\uDDFC\uDDFD\uDDFF]|\uDDE7\uD83C[\uDDE6\uDDE7\uDDE9-\uDDEF\uDDF1-\uDDF4\uDDF6-\uDDF9\uDDFB\uDDFC\uDDFE\uDDFF]|\uDDE8\uD83C[\uDDE6\uDDE8\uDDE9\uDDEB-\uDDEE\uDDF0-\uDDF5\uDDF7\uDDFA-\uDDFF]|\uDDE9\uD83C[\uDDEA\uDDEC\uDDEF\uDDF0\uDDF2\uDDF4\uDDFF]|\uDDEA\uD83C[\uDDE6\uDDE8\uDDEA\uDDEC\uDDED\uDDF7-\uDDFA]|\uDDEB\uD83C[\uDDEE-\uDDF0\uDDF2\uDDF4\uDDF7]|\uDDEC\uD83C[\uDDE6\uDDE7\uDDE9-\uDDEE\uDDF1-\uDDF3\uDDF5-\uDDFA\uDDFC\uDDFE]|\uDDED\uD83C[\uDDF0\uDDF2\uDDF3\uDDF7\uDDF9\uDDFA]|\uDDEE\uD83C[\uDDE8-\uDDEA\uDDF1-\uDDF4\uDDF6-\uDDF9]|\uDDEF\uD83C[\uDDEA\uDDF2\uDDF4\uDDF5]|\uDDF0\uD83C[\uDDEA\uDDEC-\uDDEE\uDDF2\uDDF3\uDDF5\uDDF7\uDDFC\uDDFE\uDDFF]|\uDDF1\uD83C[\uDDE6-\uDDE8\uDDEE\uDDF0\uDDF7-\uDDFB\uDDFE]|\uDDF2\uD83C[\uDDE6\uDDE8-\uDDED\uDDF0-\uDDFF]|\uDDF3\uD83C[\uDDE6\uDDE8\uDDEA-\uDDEC\uDDEE\uDDF1\uDDF4\uDDF5\uDDF7\uDDFA\uDDFF]|\uDDF4\uD83C\uDDF2|\uDDF5\uD83C[\uDDE6\uDDEA-\uDDED\uDDF0-\uDDF3\uDDF7-\uDDF9\uDDFC\uDDFE]|\uDDF6\uD83C\uDDE6|\uDDF7\uD83C[\uDDEA\uDDF4\uDDF8\uDDFA\uDDFC]|\uDDF8\uD83C[\uDDE6-\uDDEA\uDDEC-\uDDF4\uDDF7-\uDDF9\uDDFB\uDDFD-\uDDFF]|\uDDF9\uD83C[\uDDE6\uDDE8\uDDE9\uDDEB-\uDDED\uDDEF-\uDDF4\uDDF7\uDDF9\uDDFB\uDDFC\uDDFF]|\uDDFA\uD83C[\uDDE6\uDDEC\uDDF2\uDDF3\uDDF8\uDDFE\uDDFF]|\uDDFB\uD83C[\uDDE6\uDDE8\uDDEA\uDDEC\uDDEE\uDDF3\uDDFA]|\uDDFC\uD83C[\uDDEB\uDDF8]|\uDDFD\uD83C\uDDF0|\uDDFE\uD83C[\uDDEA\uDDF9]|\uDDFF\uD83C[\uDDE6\uDDF2\uDDFC]|\uDFF3\uFE0F?(?:\u200D(?:\u26A7\uFE0F?|\uD83C\uDF08))?|\uDFF4(?:\u200D\u2620\uFE0F?|\uDB40\uDC67\uDB40\uDC62\uDB40(?:\uDC65\uDB40\uDC6E\uDB40\uDC67|\uDC73\uDB40\uDC63\uDB40\uDC74|\uDC77\uDB40\uDC6C\uDB40\uDC73)\uDB40\uDC7F)?)|\uD83D(?:[\uDC3F\uDCFD\uDD49\uDD4A\uDD6F\uDD70\uDD73\uDD76-\uDD79\uDD87\uDD8A-\uDD8D\uDDA5\uDDA8\uDDB1\uDDB2\uDDBC\uDDC2-\uDDC4\uDDD1-\uDDD3\uDDDC-\uDDDE\uDDE1\uDDE3\uDDE8\uDDEF\uDDF3\uDDFA\uDECB\uDECD-\uDECF\uDEE0-\uDEE5\uDEE9\uDEF0\uDEF3]\uFE0F?|[\uDC42\uDC43\uDC46-\uDC50\uDC66\uDC67\uDC6B-\uDC6D\uDC72\uDC74-\uDC76\uDC78\uDC7C\uDC83\uDC85\uDC8F\uDC91\uDCAA\uDD7A\uDD95\uDD96\uDE4C\uDE4F\uDEC0\uDECC](?:\uD83C[\uDFFB-\uDFFF])?|[\uDC6E\uDC70\uDC71\uDC73\uDC77\uDC81\uDC82\uDC86\uDC87\uDE45-\uDE47\uDE4B\uDE4D\uDE4E\uDEA3\uDEB4-\uDEB6](?:\uD83C[\uDFFB-\uDFFF])?(?:\u200D[\u2640\u2642]\uFE0F?)?|[\uDD74\uDD90](?:\uFE0F|\uD83C[\uDFFB-\uDFFF])?|[\uDC00-\uDC07\uDC09-\uDC14\uDC16-\uDC3A\uDC3C-\uDC3E\uDC40\uDC44\uDC45\uDC51-\uDC65\uDC6A\uDC79-\uDC7B\uDC7D-\uDC80\uDC84\uDC88-\uDC8E\uDC90\uDC92-\uDCA9\uDCAB-\uDCFC\uDCFF-\uDD3D\uDD4B-\uDD4E\uDD50-\uDD67\uDDA4\uDDFB-\uDE2D\uDE2F-\uDE34\uDE37-\uDE44\uDE48-\uDE4A\uDE80-\uDEA2\uDEA4-\uDEB3\uDEB7-\uDEBF\uDEC1-\uDEC5\uDED0-\uDED2\uDED5-\uDED7\uDEDD-\uDEDF\uDEEB\uDEEC\uDEF4-\uDEFC\uDFE0-\uDFEB\uDFF0]|\uDC08(?:\u200D\u2B1B)?|\uDC15(?:\u200D\uD83E\uDDBA)?|\uDC3B(?:\u200D\u2744\uFE0F?)?|\uDC41\uFE0F?(?:\u200D\uD83D\uDDE8\uFE0F?)?|\uDC68(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:\uDC8B\u200D\uD83D)?\uDC68|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D(?:[\uDC68\uDC69]\u200D\uD83D(?:\uDC66(?:\u200D\uD83D\uDC66)?|\uDC67(?:\u200D\uD83D[\uDC66\uDC67])?)|[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uDC66(?:\u200D\uD83D\uDC66)?|\uDC67(?:\u200D\uD83D[\uDC66\uDC67])?)|\uD83E[\uDDAF-\uDDB3\uDDBC\uDDBD])|\uD83C(?:\uDFFB(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:\uDC8B\u200D\uD83D)?\uDC68\uD83C[\uDFFB-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uD83E(?:[\uDDAF-\uDDB3\uDDBC\uDDBD]|\uDD1D\u200D\uD83D\uDC68\uD83C[\uDFFC-\uDFFF])))?|\uDFFC(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:\uDC8B\u200D\uD83D)?\uDC68\uD83C[\uDFFB-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uD83E(?:[\uDDAF-\uDDB3\uDDBC\uDDBD]|\uDD1D\u200D\uD83D\uDC68\uD83C[\uDFFB\uDFFD-\uDFFF])))?|\uDFFD(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:\uDC8B\u200D\uD83D)?\uDC68\uD83C[\uDFFB-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uD83E(?:[\uDDAF-\uDDB3\uDDBC\uDDBD]|\uDD1D\u200D\uD83D\uDC68\uD83C[\uDFFB\uDFFC\uDFFE\uDFFF])))?|\uDFFE(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:\uDC8B\u200D\uD83D)?\uDC68\uD83C[\uDFFB-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uD83E(?:[\uDDAF-\uDDB3\uDDBC\uDDBD]|\uDD1D\u200D\uD83D\uDC68\uD83C[\uDFFB-\uDFFD\uDFFF])))?|\uDFFF(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:\uDC8B\u200D\uD83D)?\uDC68\uD83C[\uDFFB-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uD83E(?:[\uDDAF-\uDDB3\uDDBC\uDDBD]|\uDD1D\u200D\uD83D\uDC68\uD83C[\uDFFB-\uDFFE])))?))?|\uDC69(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:\uDC8B\u200D\uD83D)?[\uDC68\uDC69]|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D(?:[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uDC66(?:\u200D\uD83D\uDC66)?|\uDC67(?:\u200D\uD83D[\uDC66\uDC67])?|\uDC69\u200D\uD83D(?:\uDC66(?:\u200D\uD83D\uDC66)?|\uDC67(?:\u200D\uD83D[\uDC66\uDC67])?))|\uD83E[\uDDAF-\uDDB3\uDDBC\uDDBD])|\uD83C(?:\uDFFB(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:[\uDC68\uDC69]|\uDC8B\u200D\uD83D[\uDC68\uDC69])\uD83C[\uDFFB-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uD83E(?:[\uDDAF-\uDDB3\uDDBC\uDDBD]|\uDD1D\u200D\uD83D[\uDC68\uDC69]\uD83C[\uDFFC-\uDFFF])))?|\uDFFC(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:[\uDC68\uDC69]|\uDC8B\u200D\uD83D[\uDC68\uDC69])\uD83C[\uDFFB-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uD83E(?:[\uDDAF-\uDDB3\uDDBC\uDDBD]|\uDD1D\u200D\uD83D[\uDC68\uDC69]\uD83C[\uDFFB\uDFFD-\uDFFF])))?|\uDFFD(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:[\uDC68\uDC69]|\uDC8B\u200D\uD83D[\uDC68\uDC69])\uD83C[\uDFFB-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uD83E(?:[\uDDAF-\uDDB3\uDDBC\uDDBD]|\uDD1D\u200D\uD83D[\uDC68\uDC69]\uD83C[\uDFFB\uDFFC\uDFFE\uDFFF])))?|\uDFFE(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:[\uDC68\uDC69]|\uDC8B\u200D\uD83D[\uDC68\uDC69])\uD83C[\uDFFB-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uD83E(?:[\uDDAF-\uDDB3\uDDBC\uDDBD]|\uDD1D\u200D\uD83D[\uDC68\uDC69]\uD83C[\uDFFB-\uDFFD\uDFFF])))?|\uDFFF(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:[\uDC68\uDC69]|\uDC8B\u200D\uD83D[\uDC68\uDC69])\uD83C[\uDFFB-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uD83E(?:[\uDDAF-\uDDB3\uDDBC\uDDBD]|\uDD1D\u200D\uD83D[\uDC68\uDC69]\uD83C[\uDFFB-\uDFFE])))?))?|\uDC6F(?:\u200D[\u2640\u2642]\uFE0F?)?|\uDD75(?:\uFE0F|\uD83C[\uDFFB-\uDFFF])?(?:\u200D[\u2640\u2642]\uFE0F?)?|\uDE2E(?:\u200D\uD83D\uDCA8)?|\uDE35(?:\u200D\uD83D\uDCAB)?|\uDE36(?:\u200D\uD83C\uDF2B\uFE0F?)?)|\uD83E(?:[\uDD0C\uDD0F\uDD18-\uDD1F\uDD30-\uDD34\uDD36\uDD77\uDDB5\uDDB6\uDDBB\uDDD2\uDDD3\uDDD5\uDEC3-\uDEC5\uDEF0\uDEF2-\uDEF6](?:\uD83C[\uDFFB-\uDFFF])?|[\uDD26\uDD35\uDD37-\uDD39\uDD3D\uDD3E\uDDB8\uDDB9\uDDCD-\uDDCF\uDDD4\uDDD6-\uDDDD](?:\uD83C[\uDFFB-\uDFFF])?(?:\u200D[\u2640\u2642]\uFE0F?)?|[\uDDDE\uDDDF](?:\u200D[\u2640\u2642]\uFE0F?)?|[\uDD0D\uDD0E\uDD10-\uDD17\uDD20-\uDD25\uDD27-\uDD2F\uDD3A\uDD3F-\uDD45\uDD47-\uDD76\uDD78-\uDDB4\uDDB7\uDDBA\uDDBC-\uDDCC\uDDD0\uDDE0-\uDDFF\uDE70-\uDE74\uDE78-\uDE7C\uDE80-\uDE86\uDE90-\uDEAC\uDEB0-\uDEBA\uDEC0-\uDEC2\uDED0-\uDED9\uDEE0-\uDEE7]|\uDD3C(?:\u200D[\u2640\u2642]\uFE0F?|\uD83C[\uDFFB-\uDFFF])?|\uDDD1(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\uD83C[\uDF3E\uDF73\uDF7C\uDF84\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uD83E(?:[\uDDAF-\uDDB3\uDDBC\uDDBD]|\uDD1D\u200D\uD83E\uDDD1))|\uD83C(?:\uDFFB(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D(?:\uD83D\uDC8B\u200D)?\uD83E\uDDD1\uD83C[\uDFFC-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF84\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uD83E(?:[\uDDAF-\uDDB3\uDDBC\uDDBD]|\uDD1D\u200D\uD83E\uDDD1\uD83C[\uDFFB-\uDFFF])))?|\uDFFC(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D(?:\uD83D\uDC8B\u200D)?\uD83E\uDDD1\uD83C[\uDFFB\uDFFD-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF84\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uD83E(?:[\uDDAF-\uDDB3\uDDBC\uDDBD]|\uDD1D\u200D\uD83E\uDDD1\uD83C[\uDFFB-\uDFFF])))?|\uDFFD(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D(?:\uD83D\uDC8B\u200D)?\uD83E\uDDD1\uD83C[\uDFFB\uDFFC\uDFFE\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF84\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uD83E(?:[\uDDAF-\uDDB3\uDDBC\uDDBD]|\uDD1D\u200D\uD83E\uDDD1\uD83C[\uDFFB-\uDFFF])))?|\uDFFE(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D(?:\uD83D\uDC8B\u200D)?\uD83E\uDDD1\uD83C[\uDFFB-\uDFFD\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF84\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uD83E(?:[\uDDAF-\uDDB3\uDDBC\uDDBD]|\uDD1D\u200D\uD83E\uDDD1\uD83C[\uDFFB-\uDFFF])))?|\uDFFF(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D(?:\uD83D\uDC8B\u200D)?\uD83E\uDDD1\uD83C[\uDFFB-\uDFFE]|\uD83C[\uDF3E\uDF73\uDF7C\uDF84\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uD83E(?:[\uDDAF-\uDDB3\uDDBC\uDDBD]|\uDD1D\u200D\uD83E\uDDD1\uD83C[\uDFFB-\uDFFF])))?))?|\uDEF1(?:\uD83C(?:\uDFFB(?:\u200D\uD83E\uDEF2\uD83C[\uDFFC-\uDFFF])?|\uDFFC(?:\u200D\uD83E\uDEF2\uD83C[\uDFFB\uDFFD-\uDFFF])?|\uDFFD(?:\u200D\uD83E\uDEF2\uD83C[\uDFFB\uDFFC\uDFFE\uDFFF])?|\uDFFE(?:\u200D\uD83E\uDEF2\uD83C[\uDFFB-\uDFFD\uDFFF])?|\uDFFF(?:\u200D\uD83E\uDEF2\uD83C[\uDFFB-\uDFFE])?))?))")  # noqa

driver = nonebot.get_driver()

def _year(src: str) -> Tuple[date, timedelta]:
  if len(src) == 2:
    year = int(src) + 2000
  else:
    year = int(src)
  return date(year, 1, 1), timedelta(366 if calendar.isleap(year) else 365)

def _month(src: str) -> Tuple[date, timedelta]:
  year = date.today().year
  month = int(src)
  _, days = calendar.monthrange(year, month)
  return date(year, month, 1), timedelta(days)

def _day(src: str) -> Tuple[date, timedelta]:
  today = date.today()
  return date(today.year, today.month, int(src)), timedelta(1)

def _year_month(y_src: str, m_src: str) -> Tuple[date, timedelta]:
  if len(y_src) == 2:
    year = int(y_src) + 2000
  else:
    year = int(y_src)
  month = int(m_src)
  _, days = calendar.monthrange(year, month)
  return date(year, month, 1), timedelta(days)

def _month_day(m_src: str, d_src: str) -> Tuple[date, timedelta]:
  year = date.today().year
  return date(year, int(m_src), int(d_src)), timedelta(1)

def _year_month_day(y_src: str, m_src: str, d_src: str) -> Tuple[date, timedelta]:
  if len(y_src) == 2:
    year = int(y_src) + 2000
  else:
    year = int(y_src)
  return date(year, int(m_src), int(d_src)), timedelta(1)

def parse_date(src: str) -> Tuple[date, timedelta]:
  if (match := CHINESE_Y_RE.match(src)):
    return _year(match[1])
  if (match := CHINESE_M_RE.match(src)):
    return _month(match[1])
  if (match := CHINESE_D_RE.match(src)):
    return _day(match[1])
  if (match := CHINESE_YM_RE.match(src)):
    return _year_month(match[1], match[2])
  if (match := CHINESE_MD_RE.match(src)):
    return _month_day(match[1], match[2])
  if (match := CHINESE_YMD_RE.match(src)):
    return _year_month_day(match[1], match[2], match[3])
  if (match := DASH_YM_RE.match(src)):
    return _year_month(match[1], match[2])
  if (match := DASH_MD_RE.match(src)):
    return _month_day(match[1], match[2])
  if (match := DASH_YMD_RE.match(src)):
    return _year_month_day(match[1], match[2], match[3])
  if (match := SLASH_YM_RE.match(src)):
    return _year_month(match[1], match[2])
  if (match := SLASH_MD_RE.match(src)):
    return _month_day(match[1], match[2])
  if (match := SLASH_YMD_RE.match(src)):
    return _year_month_day(match[1], match[2], match[3])
  if src == "今天":
    return date.today(), timedelta(1)
  if src == "昨天":
    return date.today() - timedelta(1), timedelta(1)
  if src == "本周":
    today = date.today()
    weekday = calendar.weekday(today.year, today.month, today.day)
    return today - timedelta(weekday - 1), timedelta(7)
  if src == "上周":
    today = date.today()
    weekday = calendar.weekday(today.year, today.month, today.day)
    return today - timedelta(weekday + 6), timedelta(7)
  if src == "本月":
    today = date.today()
    _, days = calendar.monthrange(today.year, today.month)
    return date(today.year, today.month, 1), timedelta(days)
  if src == "上月":
    today = date.today()
    today -= timedelta(today.day)
    _, days = calendar.monthrange(today.year, today.month)
    return date(today.year, today.month, 1), timedelta(days)
  if src == "今年":
    year = date.today().year
    days = 366 if calendar.isleap(year) else 365
    return date(year, 1, 1), timedelta(days)
  if src == "去年":
    year = date.today().year - 1
    days = 366 if calendar.isleap(year) else 365
    return date(year, 1, 1), timedelta(days)
  raise ValueError(f"不是有效的日期: {src}")


def format_wordcloud(messages: List[str]) -> MessageSegment:
  config = CONFIG()
  texts: List[str] = []
  for i in messages:
    data: List[dict] = json.loads(i)
    plain = " ".join([x["data"]["text"] for x in data if x["type"] == "text"]).strip()
    is_command = False
    for start in driver.config.command_start:
      if start and plain.startswith(start):
        is_command = True
        break
    if is_command:
      continue
    plain = URL_RE.sub("", plain)
    plain = EMOJI_RE.sub("", plain)
    texts.append(plain)
  tfidf = TFIDF(config.idf_path)
  if config.stopwords_path:
    tfidf.set_stop_words(config.stopwords_path)
  tags = tfidf.extract_tags("\n".join(texts), 0, True)
  wc = wordcloud.WordCloud(
    config.font,
    config.width,
    config.height,
    background_color=config.bg,  # type: ignore
    colormap=config.fg
  )
  im = wc.generate_from_frequencies({word: weight for word, weight in tags}).to_image()
  return imutil.to_segment(im)


async def handle_wordcloud(bot: Bot, event: MessageEvent, arg: Message, is_user: bool) -> None:
  config = CONFIG()
  date_strs = arg.extract_plain_text().split()
  if len(date_strs) == 0:
    start_date = end_date = date.today()
    end_len = timedelta(1)
  elif len(date_strs) == 1:
    try:
      start_date, _ = end_date, end_len = parse_date(date_strs[0])
    except ValueError:
      await bot.send(event, f"不能解析日期：{date_strs[0]}")
      return
  elif len(date_strs) == 2:
    try:
      start_date, _ = parse_date(date_strs[0])
    except ValueError:
      await bot.send(event, f"不能解析日期：{date_strs[0]}")
      return
    try:
      end_date, end_len = parse_date(date_strs[1])
    except ValueError:
      await bot.send(event, f"不能解析日期：{date_strs[1]}")
      return
  else:
    await bot.send(event, PERSONAL_USAGE if is_user else GROUP_USAGE)
    return
  start_datetime = datetime.combine(start_date, time())
  end_datetime = datetime.combine(end_date, time()) + end_len
  group_id = context.get_event_context(event)
  user_id = event.user_id
  async with AsyncSession(record.engine) as session:
    query = select(record.Received.content)
    if group_id != -1:
      query = query.where(record.Received.group_id == group_id)
    if is_user:
      query = query.where(record.Received.user_id == user_id)
    result = await session.execute(
      query.where(
        record.Received.time >= start_datetime,
        record.Received.time < end_datetime
      )
      .order_by(func.random())
      .limit(config.limit)
    )
    messages: List[str] = result.scalars().all()
  end_datetime -= timedelta(seconds=1)  # 显示 23:59:59 而不是 00:00:00，以防误会
  title = f"{start_datetime:%Y-%m-%d %H:%M:%S} 到 {end_datetime:%Y-%m-%d %H:%M:%S} 的词云"
  if is_user:
    name = await context.get_card_or_name(bot, group_id, user_id)
    title = f"{name} {title}"
  await bot.send(event, title)
  try:
    seg = await misc.to_thread(format_wordcloud, messages)
  except Exception:
    logger.opt(exception=True).warning(
      f"生成个人词云失败 群: {group_id} 用户: {user_id} 从: {start_datetime} 到: {end_datetime}"
      if is_user else
      f"生成群词云失败 群: {group_id} 从: {start_datetime} 到: {end_datetime}"
    )
    await bot.send(event, "似乎什么都没有")
  else:
    await bot.send(event, seg)


GROUP_USAGE = USAGE.format("群词云")
group_wordcloud = (
  command.CommandBuilder("wordcloud.wordcloud.group", "群词云", "词云")
  .brief("查看最近的群词云")
  .usage(GROUP_USAGE)
  .in_group()
  .build()
)
@group_wordcloud.handle()
async def handle_group_wordcloud(
  bot: Bot, event: MessageEvent, arg: Message = CommandArg()
) -> None:
  await handle_wordcloud(bot, event, arg, False)


PERSONAL_USAGE = USAGE.format("个人词云")
personal_wordcloud = (
  command.CommandBuilder("wordcloud.wordcloud.personal", "个人词云", "我的词云")
  .brief("查看最近的个人词云")
  .usage(PERSONAL_USAGE)
  .build()
)
@personal_wordcloud.handle()
async def handle_personal_wordcloud(
  bot: Bot, event: MessageEvent, arg: Message = CommandArg()
) -> None:
  await handle_wordcloud(bot, event, arg, True)


async def handle_statistics(
  bot: Bot, event: MessageEvent, arg: Message, is_user: bool
) -> None:
  config = CONFIG()
  group_id = context.get_event_context(event)
  user_id = event.user_id
  today = date.today()
  is_year = arg.extract_plain_text().rstrip() == "年"
  if is_year:
    date_func = func.date(record.Received.time, "start of month")
    if today.month == 12:
      begin_time = date(today.year, 1, 1)
    else:
      begin_time = date(today.year - 1, today.month + 1, 1)
  else:
    date_func = func.date(record.Received.time)
    begin_time = today - timedelta(31)
  title = f"{'年' if is_year else '月'}发言数"
  if is_user:
    name = await context.get_card_or_name(bot, group_id, user_id)
    title = f"{name} 的{title}"
  async with AsyncSession(record.engine) as session:
    query = select([
      date_func.label("date"),
      func.count("date")
    ])
    if group_id != -1:
      query = query.where(record.Received.group_id == group_id)
    if is_user:
      query = query.where(record.Received.user_id == user_id)
    result = await session.execute(
      query
      .where(record.Received.time >= begin_time)
      .group_by("date")
    )
    result = result.all()

  def make() -> MessageSegment:
    labels = []
    counts = []
    i = 0
    curtime = begin_time
    while curtime <= today:
      labels.append(curtime.strftime("%Y-%m") if is_year else curtime.strftime("%m-%d"))
      if i < len(result) and result[i][0] == str(curtime):
        counts.append(result[i][1])
        i += 1
      else:
        counts.append(0)
      if is_year:
        if curtime.month == 12:
          curtime = date(curtime.year + 1, 1, 1)
        else:
          curtime = curtime.replace(month=curtime.month + 1)
      else:
        curtime += timedelta(1)
    font = FontProperties(fname=config.font)  # type: ignore
    fig = Figure()
    axe = fig.gca()
    if not is_year:
      fig.set_figwidth(12.8)
      fig.subplots_adjust(left=0.0625, right=0.95)
      axe.set_xmargin(0.025)
    axe.plot(labels, counts)
    for label, count in zip(labels, counts):
      axe.text(
        label, count, str(count), ha="center", va="center", fontproperties=font, color="white",
        bbox={"boxstyle": "circle", "facecolor": "#1f77b4", "linewidth": 0}
      )
    axe.set_title(title, fontproperties=font)
    for text in axe.get_xticklabels():
      text.update({"rotation": 30, "ha": "right", "fontproperties": font})
    for text in axe.get_yticklabels():
      text.update({"fontproperties": font})
    f = BytesIO()
    fig.savefig(f)
    return MessageSegment.image(f)

  await bot.send(event, await misc.to_thread(make))


group_statistics = (
  command.CommandBuilder("wordcloud.statistics.personal", "群统计", "统计")
  .brief("查看最近的个人发言数")
  .usage('''\
/群统计 - 查看最近30天的发言数，以天为单位
/群统计 年 - 查看最近一年的发言数，以月为单位''')
  .in_group()
  .build()
)
@group_statistics.handle()
async def handle_group_statistics(
  bot: Bot, event: MessageEvent, arg: Message = CommandArg()
) -> None:
  await handle_statistics(bot, event, arg, False)


personal_statistics = (
  command.CommandBuilder("wordcloud.statistics.personal", "个人统计", "我的统计")
  .brief("查看最近的个人发言数")
  .usage('''\
/个人统计 - 查看最近30天的发言数，以天为单位
/个人统计 年 - 查看最近一年的发言数，以月为单位''')
  .build()
)
@personal_statistics.handle()
async def handle_personal_statistics(
  bot: Bot, event: MessageEvent, arg: Message = CommandArg()
) -> None:
  await handle_statistics(bot, event, arg, True)


LEADERBOARD_USAGE = USAGE.format("排行")
leaderboard = (
  command.CommandBuilder("wordcloud.leaderboard", "排行")
  .brief("查看最近的发言排行")
  .usage(LEADERBOARD_USAGE)
  .build()
)
@leaderboard.handle()
async def handle_leaderboard(
  bot: Bot, event: MessageEvent, arg: Message = CommandArg()
) -> None:
  date_strs = arg.extract_plain_text().split()
  if len(date_strs) == 0:
    start_date = end_date = date.today()
    end_len = timedelta(1)
  elif len(date_strs) == 1:
    try:
      start_date, _ = end_date, end_len = parse_date(date_strs[0])
    except ValueError:
      await leaderboard.finish(f"不能解析日期：{date_strs[0]}")
  elif len(date_strs) == 2:
    try:
      start_date, _ = parse_date(date_strs[0])
    except ValueError:
      await leaderboard.finish(f"不能解析日期：{date_strs[0]}")
    try:
      end_date, end_len = parse_date(date_strs[1])
    except ValueError:
      await leaderboard.finish(f"不能解析日期：{date_strs[1]}")
  else:
    await leaderboard.finish(LEADERBOARD_USAGE)
  config = CONFIG()
  group_id = context.get_event_context(event)
  start_datetime = datetime.combine(start_date, time())
  end_datetime = datetime.combine(end_date, time()) + end_len
  async with AsyncSession(record.engine) as session:
    result = await session.execute(
      select([
        record.Received.user_id,
        func.count(record.Received.user_id).label("count")
      ])
      .group_by(record.Received.user_id).where(
        record.Received.group_id == group_id,
        record.Received.time >= start_datetime,
        record.Received.time < end_datetime
      )
      .order_by(desc("count"))
      .limit(config.leaderboard_linit)
    )
    result = result.all()
    result.reverse()  # matplotlib的y轴是反过来的
  infos: List[Tuple[Image.Image, str]] = await asyncio.gather(*[
    asyncio.gather(
      imutil.get_avatar(uid, bg=True),
      context.get_card_or_name(bot, event, uid)
    ) for uid, _ in result
  ])
  end_datetime -= timedelta(seconds=1)  # 显示 23:59:59 而不是 00:00:00，以防误会

  def make() -> MessageSegment:
    names = [name for _, name in infos]
    counts = [count for _, count in result]
    font = FontProperties(fname=config.font)  # type: ignore
    fig = Figure()
    axe = fig.gca()
    graph = axe.barh(names, counts)
    fw = fig.get_figwidth() * fig.dpi
    fh = fig.get_figheight() * fig.dpi
    width = 0.125
    for text in axe.get_xticklabels():
      text.update({"fontproperties": font})
    for text in axe.get_yticklabels():
      text.update({"fontproperties": font})
      extent = text.get_window_extent()
      width = max(width, (extent.x1 - extent.x0) / fw + 0.025)
    axe.set_title(
      f"{start_datetime:%Y-%m-%d %H:%M:%S} 到 {end_datetime:%Y-%m-%d %H:%M:%S} 的排行",
      fontproperties=font,
    )
    size = int(min(fh / len(infos), 0.1 * fw))
    fig.subplots_adjust(left=width, right=1 - (size + 1) / fw)
    x = fw - size
    y = fh / 2 - size * len(infos) / 2
    for i, (avatar, _) in enumerate(infos):
      avatar: Any = avatar.resize((size, size), imutil.scale_resample())
      fig.figimage(avatar, x, y + i * size)
    for rect, count in zip(graph, counts):
      x = rect.get_x() + rect.get_width()
      y = rect.get_y() + rect.get_height() / 2
      text = axe.text(
        x, y, str(count), ha="right", va="center", fontproperties=font, color="white"
      )
      rect_ext = rect.get_window_extent()
      text_ext = text.get_window_extent()
      if rect_ext.x1 - rect_ext.x0 < (text_ext.x1 - text_ext.x0) * 1.5:
        text.set_horizontalalignment("left")
        text.set_color("black")
    f = BytesIO()
    fig.savefig(f)
    return MessageSegment.image(f)

  await leaderboard.finish(await misc.to_thread(make))
