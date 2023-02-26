# pyright: strict
# pylama: ignore=E501 # noqa
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, List

from ..color_utils import blue_from_argb, green_from_argb, red_from_argb
from . import quantizer_map

'''
An image quantizer that divides the image's pixels into clusters by recursively cutting an RGB
cube, based on the weight of pixels in each area of the cube.

The algorithm was described by Xiaolin Wu in Graphic Gems II, published in 1991.
'''

_INDEX_BITS = 5
_SIDE_LENGTH = 33  # ((1 << INDEX_INDEX_BITS) + 1)
_TOTAL_SIZE = 35937  # SIDE_LENGTH * SIDE_LENGTH * SIDE_LENGTH


class _Directions(Enum):
  RED = 1
  GREEN = 2
  BLUE = 3


@dataclass
class _Box:
  '''
  Keeps track of the state of each box created as the Wu quantization algorithm progresses through
  dividing the image's pixels as plotted in RGB.
  '''
  r0: int = 0
  r1: int = 0
  g0: int = 0
  g1: int = 0
  b0: int = 0
  b1: int = 0
  vol: int = 0


@dataclass
class _CreateBoxesResult:
  '''Represents final result of Wu algorithm.'''
  requestedCount: int
  '''how many colors the caller asked to be returned from quantization.'''
  resultCount: int
  '''
  the actual number of colors achieved from quantization. May be lower than the requested count.
  '''


@dataclass
class _MaximizeResult:
  '''
  Represents the result of calculating where to cut an existing box in such a way to maximize
  variance between the two new boxes created by a cut.
  '''
  cutLocation: int
  maximum: float


def _getIndex(r: int, g: int, b: int) -> int:
  return (r << (_INDEX_BITS * 2)) + (r << (_INDEX_BITS + 1)) + r + (g << _INDEX_BITS) + g + b


def _volume(cube: _Box, moment: List[int]) -> int:
  return moment[_getIndex(cube.r1, cube.g1, cube.b1)] - moment[_getIndex(cube.r1, cube.g1, cube.b0)] - moment[_getIndex(cube.r1, cube.g0, cube.b1)] + moment[_getIndex(cube.r1, cube.g0, cube.b0)] - moment[_getIndex(cube.r0, cube.g1, cube.b1)] + moment[_getIndex(cube.r0, cube.g1, cube.b0)] + moment[_getIndex(cube.r0, cube.g0, cube.b1)] - moment[_getIndex(cube.r0, cube.g0, cube.b0)]


def _bottom(cube: _Box, direction: _Directions, moment: List[int]) -> int:
  if direction == _Directions.RED:
    return -moment[_getIndex(cube.r0, cube.g1, cube.b1)] + moment[_getIndex(cube.r0, cube.g1, cube.b0)] + moment[_getIndex(cube.r0, cube.g0, cube.b1)] - moment[_getIndex(cube.r0, cube.g0, cube.b0)]
  elif direction == _Directions.GREEN:
    return -moment[_getIndex(cube.r1, cube.g0, cube.b1)] + moment[_getIndex(cube.r1, cube.g0, cube.b0)] + moment[_getIndex(cube.r0, cube.g0, cube.b1)] - moment[_getIndex(cube.r0, cube.g0, cube.b0)]
  else:
    return -moment[_getIndex(cube.r1, cube.g1, cube.b0)] + moment[_getIndex(cube.r1, cube.g0, cube.b0)] + moment[_getIndex(cube.r0, cube.g1, cube.b0)] - moment[_getIndex(cube.r0, cube.g0, cube.b0)]


def _top(cube: _Box, direction: _Directions, position: int, moment: List[int]) -> int:
  if direction == _Directions.RED:
    return moment[_getIndex(position, cube.g1, cube.b1)] - moment[_getIndex(position, cube.g1, cube.b0)] - moment[_getIndex(position, cube.g0, cube.b1)] + moment[_getIndex(position, cube.g0, cube.b0)]
  elif direction == _Directions.GREEN:
    return moment[_getIndex(cube.r1, position, cube.b1)] - moment[_getIndex(cube.r1, position, cube.b0)] - moment[_getIndex(cube.r0, position, cube.b1)] + moment[_getIndex(cube.r0, position, cube.b0)]
  else:
    return moment[_getIndex(cube.r1, cube.g1, position)] - moment[_getIndex(cube.r1, cube.g0, position)] - moment[_getIndex(cube.r0, cube.g1, position)] + moment[_getIndex(cube.r0, cube.g0, position)]


class _QuantizerWu:
  def __init__(self):
    self.weights: List[int] = []
    self.momentsR: List[int] = []
    self.momentsG: List[int] = []
    self.momentsB: List[int] = []
    self.moments: List[int] = []
    self.cubes: List[_Box] = []

  def constructHistogram(self, pixels: Iterable[int]) -> None:
    self.weights = [0] * _TOTAL_SIZE
    self.momentsR = [0] * _TOTAL_SIZE
    self.momentsG = [0] * _TOTAL_SIZE
    self.momentsB = [0] * _TOTAL_SIZE
    self.moments = [0] * _TOTAL_SIZE
    countByColor = quantizer_map.quantize(pixels)
    for pixel, count in countByColor.items():
      red = red_from_argb(pixel)
      green = green_from_argb(pixel)
      blue = blue_from_argb(pixel)
      bitsToRemove = 8 - _INDEX_BITS
      iR = (red >> bitsToRemove) + 1
      iG = (green >> bitsToRemove) + 1
      iB = (blue >> bitsToRemove) + 1
      index = _getIndex(iR, iG, iB)
      self.weights[index] = (self.weights[index] if len(self.weights) > index else 0) + count
      self.momentsR[index] += count * red
      self.momentsG[index] += count * green
      self.momentsB[index] += count * blue
      self.moments[index] += count * (red * red + green * green + blue * blue)

  def computeMoments(self):
    for r in range(1, _SIDE_LENGTH):
      area = [0] * _SIDE_LENGTH
      areaR = [0] * _SIDE_LENGTH
      areaG = [0] * _SIDE_LENGTH
      areaB = [0] * _SIDE_LENGTH
      area2 = [0] * _SIDE_LENGTH
      for g in range(1, _SIDE_LENGTH):
        line = 0
        lineR = 0
        lineG = 0
        lineB = 0
        line2 = 0
        for b in range(1, _SIDE_LENGTH):
          index = _getIndex(r, g, b)
          line += self.weights[index]
          lineR += self.momentsR[index]
          lineG += self.momentsG[index]
          lineB += self.momentsB[index]
          line2 += self.moments[index]
          area[b] += line
          areaR[b] += lineR
          areaG[b] += lineG
          areaB[b] += lineB
          area2[b] += line2
          previousIndex = _getIndex(r - 1, g, b)
          self.weights[index] = self.weights[previousIndex] + area[b]
          self.momentsR[index] = self.momentsR[previousIndex] + areaR[b]
          self.momentsG[index] = self.momentsG[previousIndex] + areaG[b]
          self.momentsB[index] = self.momentsB[previousIndex] + areaB[b]
          self.moments[index] = self.moments[previousIndex] + area2[b]

  def createBoxes(self, maxColors: int) -> _CreateBoxesResult:
    self.cubes = [_Box() for _ in range(maxColors)]
    volumeVariance = [0.0] * maxColors
    self.cubes[0].r0 = 0
    self.cubes[0].g0 = 0
    self.cubes[0].b0 = 0
    self.cubes[0].r1 = _SIDE_LENGTH - 1
    self.cubes[0].g1 = _SIDE_LENGTH - 1
    self.cubes[0].b1 = _SIDE_LENGTH - 1
    generatedColorCount = maxColors
    next = 0
    for i in range(1, maxColors):
      if self.cut(self.cubes[next], self.cubes[i]):
        volumeVariance[next] = self.variance(self.cubes[next]) if self.cubes[next].vol > 1 else 0.0
        volumeVariance[i] = self.variance(self.cubes[i]) if self.cubes[i].vol > 1 else 0.0
      else:
        volumeVariance[next] = 0.0
        i -= 1
      next = 0
      temp = volumeVariance[0]
      for j in range(1, i):
        if volumeVariance[j] > temp:
          temp = volumeVariance[j]
          next = j
      if temp <= 0.0:
        generatedColorCount = i + 1
        break
    return _CreateBoxesResult(maxColors, generatedColorCount)

  def createResult(self, colorCount: int) -> List[int]:
    colors: List[int] = []
    for i in range(colorCount):
      cube = self.cubes[i]
      weight = _volume(cube, self.weights)
      if weight > 0:
        r = round(_volume(cube, self.momentsR) / weight)
        g = round(_volume(cube, self.momentsG) / weight)
        b = round(_volume(cube, self.momentsB) / weight)
        color = (255 << 24) | ((r & 0x0ff) << 16) | ((g & 0x0ff) << 8) | (b & 0x0ff)
        colors.append(color)
    return colors

  def variance(self, cube: _Box) -> float:
    dr = _volume(cube, self.momentsR)
    dg = _volume(cube, self.momentsG)
    db = _volume(cube, self.momentsB)
    xx = self.moments[_getIndex(cube.r1, cube.g1, cube.b1)] - self.moments[_getIndex(cube.r1, cube.g1, cube.b0)] - self.moments[_getIndex(cube.r1, cube.g0, cube.b1)] + self.moments[_getIndex(cube.r1, cube.g0, cube.b0)] - self.moments[_getIndex(cube.r0, cube.g1, cube.b1)] + self.moments[_getIndex(cube.r0, cube.g1, cube.b0)] + self.moments[_getIndex(cube.r0, cube.g0, cube.b1)] - self.moments[_getIndex(cube.r0, cube.g0, cube.b0)]
    hypotenuse = dr * dr + dg * dg + db * db
    return xx - hypotenuse / _volume(cube, self.weights)

  def cut(self, one: _Box, two: _Box) -> bool:
    wholeR = _volume(one, self.momentsR)
    wholeG = _volume(one, self.momentsG)
    wholeB = _volume(one, self.momentsB)
    wholeW = _volume(one, self.weights)
    maxRResult = self.maximize(one, _Directions.RED, one.r0 + 1, one.r1, wholeR, wholeG, wholeB, wholeW)
    maxGResult = self.maximize(one, _Directions.GREEN, one.g0 + 1, one.g1, wholeR, wholeG, wholeB, wholeW)
    maxBResult = self.maximize(one, _Directions.BLUE, one.b0 + 1, one.b1, wholeR, wholeG, wholeB, wholeW)
    maxR = maxRResult.maximum
    maxG = maxGResult.maximum
    maxB = maxBResult.maximum
    if maxR >= maxG and maxR >= maxB:
      if maxRResult.cutLocation < 0:
        return False
      direction = _Directions.RED
    elif maxG >= maxR and maxG >= maxB:
      direction = _Directions.GREEN
    else:
      direction = _Directions.BLUE
    two.r1 = one.r1
    two.g1 = one.g1
    two.b1 = one.b1

    if direction == _Directions.RED:
      one.r1 = maxRResult.cutLocation
      two.r0 = one.r1
      two.g0 = one.g0
      two.b0 = one.b0
    elif direction == _Directions.GREEN:
      one.g1 = maxGResult.cutLocation
      two.r0 = one.r0
      two.g0 = one.g1
      two.b0 = one.b0
    else:
      one.b1 = maxBResult.cutLocation
      two.r0 = one.r0
      two.g0 = one.g0
      two.b0 = one.b1

    one.vol = (one.r1 - one.r0) * (one.g1 - one.g0) * (one.b1 - one.b0)
    two.vol = (two.r1 - two.r0) * (two.g1 - two.g0) * (two.b1 - two.b0)
    return True

  def maximize(self, cube: _Box, direction: _Directions, first: int, last: int, wholeR: int, wholeG: int, wholeB: int, wholeW: int) -> _MaximizeResult:
    bottomR = _bottom(cube, direction, self.momentsR)
    bottomG = _bottom(cube, direction, self.momentsG)
    bottomB = _bottom(cube, direction, self.momentsB)
    bottomW = _bottom(cube, direction, self.weights)
    max = 0.0
    cut = -1
    halfR = 0
    halfG = 0
    halfB = 0
    halfW = 0
    for i in range(first, last):
      halfR = bottomR + _top(cube, direction, i, self.momentsR)
      halfG = bottomG + _top(cube, direction, i, self.momentsG)
      halfB = bottomB + _top(cube, direction, i, self.momentsB)
      halfW = bottomW + _top(cube, direction, i, self.weights)
      if halfW == 0:
        continue
      tempNumerator = (halfR * halfR + halfG * halfG + halfB * halfB) * 1.0
      tempDenominator = halfW * 1.0
      temp = tempNumerator / tempDenominator
      halfR = wholeR - halfR
      halfG = wholeG - halfG
      halfB = wholeB - halfB
      halfW = wholeW - halfW
      if halfW == 0:
        continue
      tempNumerator = (halfR * halfR + halfG * halfG + halfB * halfB) * 1.0
      tempDenominator = halfW * 1.0
      temp += tempNumerator / tempDenominator
      if temp > max:
        max = temp
        cut = i
    return _MaximizeResult(cut, max)


def quantize(pixels: Iterable[int], max_colors: int) -> List[int]:
  '''
  :param pixels: Colors in ARGB format.
  :param max_colors: The number of colors to divide the image into. A lower number of colors may be
                     returned.
  :return: Colors in ARGB format.
  '''
  quantizer = _QuantizerWu()
  quantizer.constructHistogram(pixels)
  quantizer.computeMoments()
  createBoxesResult = quantizer.createBoxes(max_colors)
  return quantizer.createResult(createBoxesResult.resultCount)
