from io import StringIO
from html.parser import HTMLParser
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

  def handle_data(self, data):
    self.f.write(data)

  def close(self) -> str:
    super().close()
    return self.f.getvalue()

def strip_html(*text: str):
  stripper = HTMLStripper()
  for i in text:
    stripper.feed(i)
  stripper.close()
  return stripper.close()
