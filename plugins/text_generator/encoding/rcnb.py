# 因为 chr233/RCNB.python 是 AGPL-3.0 协议，以下代码参考自 RCNB.js

_CR = 'rRŔŕŖŗŘřƦȐȑȒȓɌɍ'
_CC = 'cCĆćĈĉĊċČčƇƈÇȻȼ'
_CN = 'nNŃńŅņŇňƝƞÑǸǹȠȵ'
_CB = 'bBƀƁƃƄƅßÞþ'

_SC = len(_CC)
_SB = len(_CB)
_SNB = len(_CN) * _SB
_SCNB = _SC * _SNB


def _encode_byte(v: int) -> str:
  if v > 0x7F:
    i, j = divmod(v & 0x7F, _SB)
    return _CN[i] + _CB[j]
  i, j = divmod(v, _SC)
  return _CR[i] + _CC[j]


def _encode_short(v: int) -> str:
  if v > 0x7FFF:
    reverse = True
    v &= 0x7FFF
  else:
    reverse = False
  i, j = divmod(v, _SCNB)
  j, k = divmod(j, _SNB)
  k, l = divmod(k, _SB)
  if reverse:
    return _CN[k] + _CB[l] + _CR[i] + _CC[j]
  return _CR[i] + _CC[j] + _CN[k] + _CB[l]


def _decode_byte(c: str) -> int:
  try:
    result = _CR.index(c[0]) * _SC + _CC.index(c[1])
    nb = False
  except ValueError:
    result = _CN.index(c[0]) * _SB + _CB.index(c[1])
    nb = True
  if result > 0x7f:
    raise ValueError("RC/NB overflow")
  return result | 0x80 if nb else result


def _decode_short(c: str) -> int:
  reverse = c[0] not in _CR
  if reverse:
    idx = [_CR.index(c[2]), _CC.index(c[3]), _CN.index(c[0]), _CB.index(c[1])]
  else:
    idx = [_CR.index(c[0]), _CC.index(c[1]), _CN.index(c[2]), _CB.index(c[3])]
  result = idx[0] * _SCNB + idx[1] * _SNB + idx[2] * _SB + idx[3]
  if result > 0x7FFF:
    raise ValueError("RCNB overflow")
  return result | 0x8000 if reverse else result


def encode(v: bytes) -> str:
  result = []
  for i in range(0, len(v) - 1, 2):
    result.append(_encode_short((v[i] << 8) | v[i + 1]))
  if len(v) & 1:
    result.append(_encode_byte(v[-1]))
  return "".join(result)


def decode(c: str) -> bytes:
  if len(c) & 1:
    raise ValueError("Invalid length")
  result = bytearray()
  for i in range(0, len(c) - 3, 4):
    v = _decode_short(c[i:i + 4])
    result.append(v >> 8)
    result.append(v & 0xFF)
  if len(c) & 2:
    result.append(_decode_byte(c[-2:]))
  return bytes(result)
