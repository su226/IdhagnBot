# 代码移植至 https://github.com/stdlib-js/random-base-binomial/blob/main/lib/sample2.js
# 至少不依赖NumPy了（）
import math
import random as random_

ONE_SIXTH = 1 / 6
ONE_12 = 1 / 12
ONE_360 = 1 / 360
ONE_1260 = 1 / 1260


def _correction(k: float) -> float:
  k += 1
  v = k ** 2
  return (ONE_12 - ((ONE_360 - (ONE_1260 / v)) / v)) / k


def sample(n: int, p: float, random: random_.Random | None = None) -> int:
  rand = random.random if random else random_.random

  m = math.floor((n + 1) * p)
  nm = n - m + 1

  q = 1.0 - p

  r = p / q
  nr = (n + 1) * r

  npq = n * p * q
  snpq = math.sqrt(npq)

  b = 1.15 + (2.53 * snpq)
  a = -0.0873 + (0.0248 * b) + (0.01 * p)
  c = (n * p) + 0.5

  alpha = (2.83 + (5.1 / b)) * snpq

  vr = 0.92 - (4.2 / b)
  urvr = 0.86 * vr

  h = (m + 0.5) * math.log((m + 1) / (r * nm))
  h += _correction(m) + _correction(n - m)

  while True:
    v = rand()
    if v <= urvr:
      u = (v / vr) - 0.43
      r = (u * ((2.0 * a / (0.5 - abs(u))) + b)) + c
      return math.floor(r)
    if v >= vr:
      u = rand() - 0.5
    else:
      u = (v / vr) - 0.93
      u = (math.copysign(1, u) * 0.5) - u
      v = vr * rand()
    us = 0.5 - abs(u)
    k = math.floor((u * ((2.0 * a / us) + b)) + c)
    if k < 0 or k > n:
      continue
    v = v * alpha / ((a / (us * us)) + b)
    km = abs(k - m)
    if km > 15:
      v = math.log(v)
      rho = km / npq
      tmp = ((km / 3) + 0.625) * km
      tmp += ONE_SIXTH
      tmp /= npq
      rho *= tmp + 0.5
      t = -(km * km) / (2.0 * npq)
      if v < t - rho:
        return k
      if v <= t + rho:
        nk = n - k + 1
        x = h + ((n + 1) * math.log(nm / nk))
        x += (k + 0.5) * math.log(nk * r / (k + 1))
        x += -(_correction(k) + _correction(n - k))
        if v <= x:
          return k
    else:
      f = 1.0
      if m < k:
        for i in range(m, k + 1):
          f *= (nr / i) - r
      elif m > k:
        # JS除以0不会出错，而是Infinity
        if k == 0:
          v = math.inf
        else:
          for i in range(k, m + 1):
            v *= (nr / i) - r
      if v <= f:
        return k
