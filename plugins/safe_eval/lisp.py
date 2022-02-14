from typing import Any
import operator

class Symbol(str): pass
Literal = int | float | Symbol
class Expression(list): pass
# Parentheses = NewType("Parentheses", Expression)
# Brackets = NewType("Brackets", Expression)
# Braces = NewType("Braces", Expression)
Code = Expression | Literal

class Syntax:
  def __call__(env: dict, expressions: list[Expression]) -> Any:
    raise NotImplementedError

def to_literal(token: str) -> Literal:
  try: return int(token)
  except: pass
  try: return float(token)
  except: pass
  return Symbol(token)

def parse(code: str) -> list[Code]:
  tokens = code.replace("(", " ( ").replace(")", " ) ").split() # STUB
  tree = []
  level = 0
  def append(token):
    cur = tree
    for _ in range(level):
      cur = cur[-1]
    cur.append(token)
  for token in tokens:
    if token == "(":
      append(Expression([]))
      level += 1
    elif token == ")":
      if level == 0:
        raise ValueError("Unexpected \")\"")
      level -= 1
    else:
      append(to_literal(token))
  if level != 0:
    raise ValueError("Unmatched parentheses")
  return tree

def format(code: Code) -> str:
  if isinstance(code, Expression):
    return "(" + " ".join(map(format, code)) + ")"
  else:
    return str(code)

def eval(code: Code, env: dict) -> Any:
  if isinstance(code, Expression):
    if len(code) == 0:
      raise ValueError(f"Empty expression.")
    func = code[0]
    if isinstance(func, Symbol):
      if func not in env:
        raise NameError(f"Identifier with name {func} doesn't exist.")
      func = env[func]
    if isinstance(func, Syntax):
      return func(env, code[1:])
    else:
      return func(*map(lambda x: eval(x, env), code[1:]))
  elif isinstance(code, Symbol):
    if code not in env:
      raise NameError(f"Identifier with name {code} doesn't exist.")
    return env[code]
  else:
    return code

def math_env():
  return {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "**": operator.pow,
    "/": operator.truediv,
    "//": operator.floordiv,
    "%": operator.mod,
  }
