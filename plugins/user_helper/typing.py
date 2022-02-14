from typing import TYPE_CHECKING, Callable, Awaitable, Type, TypeVar
from nonebot.matcher import Matcher
if TYPE_CHECKING:
  from . import Arguments as _Arguments

Arguments: Type["_Arguments"] = ...
Callback = Callable[[Matcher, Arguments], Awaitable[None]]
T = TypeVar("T")
class Helper:
  def command(names: str | list[str], brief: str = "", usage: str | list[str] = "", contexts: int | list[int] = []) -> Callable[[Callback], Callback]: ...
  def weighted_choice(choices: list[T | tuple[T, int]]) -> T: ...
