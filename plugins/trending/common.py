from html.parser import HTMLParser
from io import StringIO

from pydantic import BaseModel


class Item(BaseModel):
  url: str
  title: str
  image: str
  content: str


class HTMLStripper(HTMLParser):
  def __init__(self):
    super().__init__()
    self.f = StringIO()

  def handle_data(self, data: str) -> None:
    self.f.write(data)

  def getvalue(self) -> str:
    return self.f.getvalue()


def strip_html(*text: str):
  stripper = HTMLStripper()
  for i in text:
    stripper.feed(i)
  stripper.close()
  return stripper.getvalue()
