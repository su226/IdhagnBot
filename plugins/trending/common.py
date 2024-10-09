from pydantic import BaseModel


class Item(BaseModel):
  url: str
  title: str
  image: str
  content: str
