# pyright: strict
# ruff: noqa: E501
# https://github.com/acheong08/OpenAIAuth
# 使用 AIOHTTP 重写
import re
from typing import Optional
from urllib.parse import quote as encodeuri

from aiohttp import ClientSession


class AuthError(Exception):
  """Base error class"""

  location: str
  status_code: int
  details: str

  def __init__(self, location: str, status_code: int, details: str):
    self.location = location
    self.status_code = status_code
    self.details = details


class OpenAIAuth:
  """OpenAI Authentication Reverse Engineered"""

  def __init__(self, email_address: str, password: str, session: ClientSession, user_agent: str, proxy: Optional[str] = None) -> None:
    self.email_address = email_address
    self.password = password
    self.session = session
    self.user_agent = user_agent
    self.proxy = proxy
    self.session_token: Optional[str] = None
    self.access_token: Optional[str] = None

  async def login(self) -> str:
    # In part two, We make a request to https://explorer.api.openai.com/api/auth/csrf and grab a fresh csrf token
    url = "https://explorer.api.openai.com/api/auth/csrf"
    headers = {
      "Host": "explorer.api.openai.com",
      "Accept": "*/*",
      "Connection": "keep-alive",
      "User-Agent": self.user_agent,
      "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
      "Referer": "https://explorer.api.openai.com/auth/login",
      "Accept-Encoding": "gzip, deflate, br",
    }
    async with self.session.get(url, headers=headers, proxy=self.proxy) as response:
      if response.status != 200 or "json" not in response.headers["Content-Type"]:
        raise AuthError(
          location="begin",
          status_code=response.status,
          details=await response.text(),
        )
      csrf_token = (await response.json())["csrfToken"]
    # We reuse the token from part to make a request to /api/auth/signin/auth0?prompt=login
    url = "https://explorer.api.openai.com/api/auth/signin/auth0?prompt=login"
    payload = f"callbackUrl=%2F&csrfToken={csrf_token}&json=true"
    headers = {
      "Host": "explorer.api.openai.com",
      "User-Agent": self.user_agent,
      "Content-Type": "application/x-www-form-urlencoded",
      "Accept": "*/*",
      "Sec-Gpc": "1",
      "Accept-Language": "en-US,en;q=0.8",
      "Origin": "https://explorer.api.openai.com",
      "Sec-Fetch-Site": "same-origin",
      "Sec-Fetch-Mode": "cors",
      "Sec-Fetch-Dest": "empty",
      "Referer": "https://explorer.api.openai.com/auth/login",
      "Accept-Encoding": "gzip, deflate",
    }
    async with self.session.post(url, headers=headers, data=payload, proxy=self.proxy) as response:
      if response.status != 200 or "json" not in response.headers["Content-Type"]:
        raise AuthError(
          location="__part_one",
          status_code=response.status,
          details=await response.text(),
        )
      url = (await response.json())["url"]
      if url == "https://explorer.api.openai.com/api/auth/error?error=OAuthSignin" or "error" in url:
        raise AuthError(
          location="__part_one",
          status_code=response.status,
          details="You have been rate limited. Please try again later.",
        )
    # We make a GET request to url
    headers = {
      "Host": "auth0.openai.com",
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "Connection": "keep-alive",
      "User-Agent": self.user_agent,
      "Accept-Language": "en-US,en;q=0.9",
      "Referer": "https://explorer.api.openai.com/",
    }
    async with self.session.get(url, headers=headers, proxy=self.proxy) as response:
      if response.status not in {200, 302}:
        raise AuthError(
          location="__part_two",
          status_code=response.status,
          details=await response.text(),
        )
      state = re.findall(r"state=(.*)", await response.text())[0]
      state = state.split('"')[0]
    # We use the state to get the login page
    url = f"https://auth0.openai.com/u/login/identifier?state={state}"
    headers = {
      "Host": "auth0.openai.com",
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "Connection": "keep-alive",
      "User-Agent": self.user_agent,
      "Accept-Language": "en-US,en;q=0.9",
      "Referer": "https://explorer.api.openai.com/",
    }
    async with self.session.get(url, headers=headers, proxy=self.proxy) as response:
      if response.status != 200:
        raise AuthError(
          location="__part_three",
          status_code=response.status,
          details=await response.text(),
        )
    # We make a POST request to the login page with the captcha, email
    url = f"https://auth0.openai.com/u/login/identifier?state={state}"
    email_urlencode = encodeuri(self.email_address)
    payload = (
      f"state={state}&username={email_urlencode}&js-available=false"
      "&webauthn-available=true&is-brave=false&webauthn-platform-available=true&action=default"
    )
    headers = {
      "Host": "auth0.openai.com",
      "Origin": "https://auth0.openai.com",
      "Connection": "keep-alive",
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "User-Agent": self.user_agent,
      "Referer": f"https://auth0.openai.com/u/login/identifier?state={state}",
      "Accept-Language": "en-US,en;q=0.9",
      "Content-Type": "application/x-www-form-urlencoded",
    }
    async with self.session.post(url, headers=headers, data=payload, proxy=self.proxy) as response:
      if response.status not in {302, 200}:
        raise AuthError(
          location="__part_four",
          status_code=response.status,
          details="Your email address is invalid.",
        )
    # We enter the password
    url = f"https://auth0.openai.com/u/login/password?state={state}"
    password_urlencode = encodeuri(self.password)
    payload = f"state={state}&username={email_urlencode}&password={password_urlencode}&action=default"
    headers = {
      "Host": "auth0.openai.com",
      "Origin": "https://auth0.openai.com",
      "Connection": "keep-alive",
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "User-Agent": self.user_agent,
      "Referer": f"https://auth0.openai.com/u/login/password?state={state}",
      "Accept-Language": "en-US,en;q=0.9",
      "Content-Type": "application/x-www-form-urlencoded",
    }
    async with self.session.post(url, headers=headers, allow_redirects=False, data=payload, proxy=self.proxy) as response:
      if response.status not in (200, 302):
        raise AuthError(
          location="__part_five",
          status_code=response.status,
          details="Your credentials are invalid.",
        )
      new_state = re.findall(r"state=(.*)", await response.text())[0]
      new_state = new_state.split('"')[0]
    url = f"https://auth0.openai.com/authorize/resume?state={new_state}"
    headers = {
      "Host": "auth0.openai.com",
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "Connection": "keep-alive",
      "User-Agent": self.user_agent,
      "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
      "Referer": f"https://auth0.openai.com/u/login/password?state={state}",
    }
    async with self.session.get(url, headers=headers, allow_redirects=False, proxy=self.proxy) as response:
      if response.status != 302:
        raise AuthError(
          location="__part_six",
          status_code=response.status,
          details=await response.text(),
        )
      # Print redirect url
      previous_url = url
      url = response.headers["location"]
    headers = {
      "Host": "explorer.api.openai.com",
      "Accept": "application/json",
      "Connection": "keep-alive",
      "User-Agent": self.user_agent,
      "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
      "Referer": previous_url,
    }
    async with self.session.get(url, headers=headers, allow_redirects=False, proxy=self.proxy) as response:
      if response.status != 302:
        raise AuthError(
          location="__part_seven",
          status_code=response.status,
          details=await response.text(),
        )
      self.session_token = response.cookies["__Secure-next-auth.session-token"].value
    return self.session_token

  async def get_access_token(self) -> str:
    """Gets access token"""
    if not self.session_token:
      raise ValueError("login should be called first")
    self.session.cookie_jar.update_cookies({
      "__Secure-next-auth.session-token": self.session_token,
    })
    async with self.session.get("https://explorer.api.openai.com/api/auth/session", proxy=self.proxy) as response:
      if response.status != 200:
        raise AuthError(
          location="get_access_token",
          status_code=response.status,
          details=await response.text(),
        )
      self.access_token = access_token = (await response.json())["accessToken"]
      return access_token
