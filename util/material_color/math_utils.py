# pyright: strict
from typing import Literal, Tuple, TypeVar

'''Utility methods for mathematical operations.'''

Vec3f = Tuple[float, float, float]
Mat3x3f = Tuple[Vec3f, Vec3f, Vec3f]
Signum = Literal[-1, 0, 1]
TNumber = TypeVar("TNumber", int, float)


def signum(num: float) -> Signum:
  '''
  The signum function.
  :return: 1 if num > 0, -1 if num < 0, and 0 if num = 0
  '''
  if num < 0:
    return -1
  elif num == 0:
    return 0
  else:
    return 1


def lerp(start: float, stop: float, amount: float) -> float:
  '''
  The linear interpolation function.
  :return: start if amount = 0 and stop if amount = 1
  '''
  return (1.0 - amount) * start + amount * stop


def clamp(min: TNumber, max: TNumber, input: TNumber) -> TNumber:
  '''
  Clamps an integer between two integers.
  :return: input when min <= input <= max, and either min or max otherwise.
  '''
  if input < min:
    return min
  elif input > max:
    return max
  return input


def sanitize_degrees(degrees: TNumber) -> TNumber:
  '''
  Sanitizes a degree measure as an integer.
  :return: a degree measure between 0 (inclusive) and 360 (exclusive).
  '''
  degrees = degrees % 360
  if degrees < 0:
    degrees = degrees + 360
  return degrees


def difference_degrees(a: float, b: float) -> float:
  '''Distance of two points on a circle, represented using degrees.'''
  return 180.0 - abs(abs(a - b) - 180.0)


def matrix_multiply(row: Vec3f, matrix: Mat3x3f) -> Vec3f:
  '''Multiplies a 1x3 row vector with a 3x3 matrix.'''
  a = row[0] * matrix[0][0] + row[1] * matrix[0][1] + row[2] * matrix[0][2]
  b = row[0] * matrix[1][0] + row[1] * matrix[1][1] + row[2] * matrix[1][2]
  c = row[0] * matrix[2][0] + row[1] * matrix[2][1] + row[2] * matrix[2][2]
  return (a, b, c)


def point_distance(from_: Vec3f, to: Vec3f) -> float:
  '''
  Standard CIE 1976 delta E formula also takes the square root, unneeded here. This method is used
  by quantization algorithms to compare distance, and the relative ordering is the same, with or
  without a square root.

  This relatively minor optimization is helpful because this method is called at least once for
  each pixel in an image.
  '''
  dL = from_[0] - to[0]
  dA = from_[1] - to[1]
  dB = from_[2] - to[2]
  return dL * dL + dA * dA + dB * dB
