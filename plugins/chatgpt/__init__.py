import asyncio
import json
import pathlib
import time
import uuid
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from loguru import logger

import nonebot
from aiohttp.client_exceptions import ClientResponseError
from apscheduler.schedulers.base import JobLookupError
from nonebot.adapters.onebot.v11 import Message, MessageEvent, MessageSegment
from nonebot.params import CommandArg
from playwright.async_api import async_playwright
from pydantic import BaseModel

from util import command, configs, context, misc, permission

nonebot.require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler


class Config(BaseModel):
  token: Optional[str] = None
  refresh_interval: float = 1800
  user_agent: str = "Mozilla/5.0 (X11; Linux x86_64; rv:107.0) Gecko/20100101 Firefox/107.0"
  proxy: Optional[str] = None
  timeout: Optional[float] = 60
  at_bot: misc.EnableSet = misc.EnableSet.false()
  image_width: int = 320
  image_scale: float = 2


@dataclass
class Conversation:
  conversation_id: str
  parent_id: str


class State(BaseModel):
  last_refresh: float = 0
  session_token: str = ""
  access_token: str = ""
  conversations: Dict[str, Conversation] = {}


CONFIG = configs.SharedConfig("chatgpt", Config, "eager")
STATE = configs.SharedState("chatgpt", State)
SESSION_TOKEN_KEY = "__Secure-next-auth.session-token"
API_BASE = "https://chat.openai.com/"
SESSION_API = API_BASE + "api/auth/session"
CHAT_API = API_BASE + "backend-api/conversation"
URL = (pathlib.Path(__file__).resolve().parent / "index.html").as_uri()


@CONFIG.onload()
def config_onload(prev: Optional[Config], curr: Config) -> None:
  try:
    scheduler.remove_job("chatgpt_session_refresh")
  except JobLookupError:
    pass
  scheduler.add_job(
    refresh_token, "interval", id="chatgpt_session_refresh", seconds=curr.refresh_interval
  )


def check_at_bot(event: MessageEvent) -> bool:
  config = CONFIG()
  return event.is_tome() and bool(config.token) and config.at_bot[event] and not event.reply
at_bot = nonebot.on_message(
  check_at_bot,
  context.build_permission(("chatgpt", "chat", "at_bot"), permission.Level.MEMBER)
)
chatgpt_cmd = (
  command.CommandBuilder("chatgpt.chat", "ChatGPT", "chatgpt")
  .brief("ChatGPT AI聊天")
  .usage("内容来自 ChatGPT，与 IdhagnBot 无关")
  .build()
)
@at_bot.handle()
@chatgpt_cmd.handle()
async def handle_at_bot(event: MessageEvent, arg: Optional[Message] = CommandArg()) -> None:
  prompt = arg or event.message
  session_id = event.get_session_id()
  state = STATE()
  try:
    response, state.conversations[session_id] = await get_response(
      prompt.extract_plain_text(),
      state.conversations.get(session_id, None)
    )
    STATE.dump()
    msg = "以下回复来自 ChatGPT，与 IdhagnBot 无关\n" + await render_markdown(response)
  except asyncio.TimeoutError:
    msg = "ChatGPT 响应超时"
  except ClientResponseError as e:
    msg = f"ChatGPT 响应了一个 HTTP 错误：{e.status} {e.message}"
  await at_bot.finish(MessageSegment.at(event.user_id) + msg)


reset_chatgpt = (
  command.CommandBuilder("chatgpt.reset", "重置ChatGPT", "重置chatgpt")
  .brief("重置 ChatGPT 会话")
  .build()
)
@reset_chatgpt.handle()
async def handle_reset_chatgpt(event: MessageEvent) -> None:
  state = STATE()
  session_id = event.get_session_id()
  if session_id in state.conversations:
    del state.conversations[session_id]
    STATE.dump()
  await reset_chatgpt.finish("已重置 ChatGPT 会话")


async def refresh_token() -> None:
  http = misc.http()
  config = CONFIG()
  if not config.token:
    return
  state = STATE()
  cookies = {SESSION_TOKEN_KEY: state.session_token or config.token}
  headers = {"User-Agent": config.user_agent}
  async with http.get(
    SESSION_API, cookies=cookies, headers=headers, proxy=config.proxy, timeout=config.timeout
  ) as response:
    logger.info(f"刷新 ChatGPT Token: {response.status}")
    data = await response.json()
    state.last_refresh = time.time()
    state.session_token = response.cookies[SESSION_TOKEN_KEY].value
    state.access_token = data["accessToken"]
  STATE.dump()


async def get_response(
  prompt: str, conversation: Optional[Conversation] = None
) -> Tuple[str, Conversation]:
  state = STATE()
  if not state.access_token:
    await refresh_token()
  config = CONFIG()
  id = str(uuid.uuid4())
  headers = {
    "Authorization": f"Bearer {state.access_token}",
    "User-Agent": config.user_agent,
  }
  cookies = {SESSION_TOKEN_KEY: state.session_token}
  payload = {
    "action": "next",
    "messages": [
      {
        "id": id,
        "role": "user",
        "content": {"content_type": "text", "parts": [prompt]},
      }
    ],
    "model": "text-davinci-002-render",
  }
  if conversation:
    payload.update(
      conversation_id=conversation.conversation_id,
      parent_message_id=conversation.parent_id,
    )
  else:
    payload.update(parent_message_id=str(uuid.uuid4()))
  http = misc.http()
  async with http.post(
    CHAT_API, headers=headers, cookies=cookies, json=payload,
    proxy=config.proxy, timeout=config.timeout, raise_for_status=True
  ) as response:
    text = await response.text()
  lines = text.splitlines()
  data = json.loads(lines[-4][6:])
  conversation = Conversation(data["conversation_id"], data["message"]["id"])
  return data["message"]["content"]["parts"][0], conversation


async def render_markdown(content: str) -> MessageSegment:
  config = CONFIG()
  async with async_playwright() as p:
    browser = await misc.launch_playwright(p)
    page = await browser.new_page(
      viewport={"width": config.image_width, "height": 1},
      device_scale_factor=config.image_scale
    )
    await page.goto(URL)
    await page.evaluate("render", content)
    data = await page.screenshot(full_page=True)
  return MessageSegment.image(data)
