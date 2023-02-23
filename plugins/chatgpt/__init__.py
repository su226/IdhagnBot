import asyncio
import json
import pathlib
import uuid
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import nonebot
from aiohttp import ClientSession
from loguru import logger
from nonebot.adapters.onebot.v11 import Message, MessageEvent, MessageSegment
from nonebot.params import CommandArg
from playwright.async_api import async_playwright
from pydantic import BaseModel

from util import command, configs, context, misc, permission
from util.api_common.openai_auth import AuthError, OpenAIAuth


class Config(BaseModel):
  email: str = ""
  password: str = ""
  user_agent: str = "Mozilla/5.0 (X11; Linux x86_64; rv:107.0) Gecko/20100101 Firefox/107.0"
  proxy: Optional[str] = None
  login_proxy: Optional[str] = None
  timeout: Optional[float] = 360
  at_bot: misc.EnableSet = misc.EnableSet.false()
  image_width: int = 320
  image_scale: float = 2
  # 老模型：text-davinci-002-render
  # 新免费模型（比老模型快）：text-davinci-002-render-sha
  # 付费模型：text-davinci-002-render-paid
  model: str = "text-davinci-002-render-sha"

  @property
  def can_login(self) -> bool:
    return bool(self.email and self.password)

  async def login(self) -> Tuple[str, str]:
    async with ClientSession(connector=misc.http().connector) as session:
      auth = OpenAIAuth(self.email, self.password, session, self.user_agent, self.login_proxy)
      session_token = await auth.login()
      access_token = await auth.get_access_token()
    return session_token, access_token


@dataclass
class Conversation:
  conversation_id: str
  parent_id: str


class State(BaseModel):
  session_token: str = ""
  access_token: str = ""
  conversations: Dict[str, Conversation] = {}

  @property
  def logged_in(self) -> bool:
    return bool(self.session_token and self.access_token)


CONFIG = configs.SharedConfig("chatgpt", Config, "eager")
STATE = configs.SharedState("chatgpt", State)
SESSION_TOKEN_KEY = "__Secure-next-auth.session-token"
CHAT_API = "https://apps.openai.com/api/conversation"
URL = (pathlib.Path(__file__).resolve().parent / "index.html").as_uri()


def check_at_bot(event: MessageEvent) -> bool:
  config = CONFIG()
  return event.is_tome() and bool(config.can_login) and config.at_bot[event] and not event.reply
at_bot = nonebot.on_message(
  check_at_bot,
  context.build_permission(("chatgpt", "chat", "at_bot"), permission.Level.MEMBER)
)
chatgpt_cmd = (
  command.CommandBuilder("chatgpt.chat", "ChatGPT", "chatgpt")
  .brief("ChatGPT AI聊天")
  .usage("内容来自 ChatGPT，与 IdhagnBot 无关")
  .rule(lambda: CONFIG().can_login)
  .help_condition(lambda _: CONFIG().can_login)
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
  except AuthError as e:
    logger.exception(
      f"ChatGPT 登录失败\nlocation: {e.location}\nstatus: {e.status_code}\ndetails: {e.details}"
    )
    msg = "ChatGPT 登录失败，请联系机器人开发者"
  await at_bot.finish(MessageSegment.at(event.user_id) + msg)


reset_chatgpt = (
  command.CommandBuilder("chatgpt.reset", "重置ChatGPT", "重置chatgpt")
  .brief("重置 ChatGPT 会话")
  .rule(lambda: bool(CONFIG().can_login))
  .help_condition(lambda _: bool(CONFIG().can_login))
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


async def get_response(
  prompt: str, conversation: Optional[Conversation] = None
) -> Tuple[str, Conversation]:
  config = CONFIG()
  state = STATE()
  id = str(uuid.uuid4())
  payload = {
    "action": "next",
    "messages": [
      {
        "id": id,
        "role": "user",
        "content": {"content_type": "text", "parts": [prompt]},
      }
    ],
    "model": config.model,
  }
  if conversation:
    payload.update(
      conversation_id=conversation.conversation_id,
      parent_message_id=conversation.parent_id,
    )
  else:
    payload.update(parent_message_id=str(uuid.uuid4()))

  while True:
    cookies = {SESSION_TOKEN_KEY: state.session_token}
    headers = {
      "Authorization": f"Bearer {state.access_token}",
      "User-Agent": config.user_agent,
    }
    http = misc.http()
    if state.logged_in:
      async with http.post(
        CHAT_API, headers=headers, cookies=cookies, json=payload,
        proxy=config.proxy, timeout=config.timeout
      ) as response:
        if response.status == 200:
          text = await response.text()
          break
    state.session_token, state.access_token = await config.login()
    STATE.dump()
    cookies[SESSION_TOKEN_KEY] = state.session_token
    headers["Authorization"] = f"Bearer {state.access_token}"
    async with http.post(
      CHAT_API, headers=headers, cookies=cookies, json=payload,
      proxy=config.proxy, timeout=config.timeout, raise_for_status=True
    ) as response:
      text = await response.text()
      break

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
