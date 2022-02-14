from typing import Callable, Sequence, TypeVar
import re
import operator

T = TypeVar("T")
def contains(val: T | set[T], seq: Sequence[T]):
  if isinstance(val, set):
    return len(val.intersection(seq)) > 0
  else:
    return val in seq

def not_contains(val: T | set[T], seq: Sequence[T]):
  if isinstance(val, set):
    return len(val.intersection(seq)) == 0
  else:
    return val not in seq

class Condition:
  COMPARISON_RE = re.compile(r"^\s*([A-Za-z]+)\s*(<|<=|==?|>=|>|!=|~=)\s*(-?\d+)\s*$")
  INCLUDE_RE = re.compile(r"^\s*([A-Za-z]+)\s*([!\?])\s*\[((?:\s*(?:-?\d+)\s*,)*\s*(?:-?\d+))\s*,?\s*\]\s*$")
  OPERATORS = {
    "<": operator.lt,
    "<=": operator.le,
    "=": operator.eq,
    "==": operator.eq,
    ">=": operator.ge,
    ">": operator.gt,
    "!=": operator.ne,
    "~=": operator.ne,
    "?": contains,
    "!": not_contains,
  }
  FALSE: "NoopCondition"
  TRUE: "NoopCondition"

  @classmethod
  def parse(cls, data: str) -> "Condition":
    tree = []
    level = 0
    def append(value):
      cur = tree
      for _ in range(level):
        cur = cur[-1]
      cur.append(value)
    for ch in data:
      if ch == '(':
        append([])
        level += 1
      elif ch == ')':
        if level == 0:
          raise ValueError("Unmatched right parentheses")
        level -= 1
      elif ch != " ":
        append(ch)
    if level != 0:
      raise ValueError("Unmatched left parentheses")
    return cls.build(tree)

  @classmethod
  def build(cls, tree: list) -> "Condition":
    while len(tree) == 1:
      tree = tree[0]
    try:
      index = tree.index("&")
    except ValueError:
      pass
    else:
      return BoolCondition(cls.build(tree[:index]), operator.and_, cls.build(tree[index + 1:]))
    try:
      index = tree.index("|")
    except ValueError:
      pass
    else:
      return BoolCondition(cls.build(tree[:index]), operator.or_, cls.build(tree[index + 1:]))
    exp = "".join(tree)
    if include := cls.INCLUDE_RE.match(exp):
      return VarCondition(include[1], cls.OPERATORS[include[2]], [int(x) for x in include[3].split(",")])
    elif comparison := cls.COMPARISON_RE.match(exp):
      return VarCondition(comparison[1], cls.OPERATORS[comparison[2]], int(comparison[3]))
    raise ValueError("Unknown condition")
  
  def __call__(self, **vars) -> bool:
    raise NotImplementedError
    
  def _pformat(self, indention: str, level: int) -> str:
    return repr(self)

  def pformat(self, indention: str = "  ") -> str:
    return self._pformat(indention, 0)

class NoopCondition(Condition):
  def __init__(self, value: bool) -> None:
    self.value = value

  def __repr__(self) -> str:
    return f"NoopCondition({self.value})"

  def __call__(self, **vars) -> bool:
    return self.value

Condition.FALSE = NoopCondition(False)
Condition.TRUE = NoopCondition(True)

class BoolCondition(Condition):
  def __init__(self, left: Condition, operator: Callable[[bool, bool], bool], right: Condition):
    self.left = left
    self.operator = operator
    self.right = right

  def __call__(self, **vars) -> bool:
    return self.operator(self.left(**vars), self.right(**vars))

  def __repr__(self) -> str:
    return f"BoolCondition({repr(self.left)}, {repr(self.operator)}, {repr(self.right)})"
    
  def _pformat(self, indention: str, level: int) -> str:
    level += 1
    current = indention * level
    return f'''BoolCondition(
{current}{self.left._pformat(indention, level)},
{current}{repr(self.operator)},
{current}{self.right._pformat(indention, level)})'''

TRight = TypeVar("TRight")
class VarCondition(Condition):
  def __init__(self, key: str, operator: Callable[[int, TRight], bool], right: TRight) -> None:
    super().__init__()
    self.key = key
    self.operator = operator
    self.right = right
  
  def __call__(self, **vars) -> bool:
    return self.operator(vars[self.key], self.right)

  def __repr__(self) -> str:
    return f"VarCondition({repr(self.key)}, {repr(self.operator)}, {repr(self.right)})"
