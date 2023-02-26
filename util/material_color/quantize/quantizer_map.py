# pyright: strict
from typing import Iterable, OrderedDict

from ..color_utils import alpha_from_argb

'''
Quantizes an image into a map, with keys of ARGB colors, and values of the number of times that
color appears in the image.
'''

def quantize(pixels: Iterable[int]) -> OrderedDict[int, int]:
  '''
  :param pixels: Colors in ARGB format.
  :return: A Map with keys of ARGB colors, and values of the number of times the color appears in
           the image.
  '''
  countByColor = OrderedDict[int, int]()
  for pixel in pixels:
    alpha = alpha_from_argb(pixel)
    if alpha < 255:
      continue
    countByColor[pixel] = (countByColor[pixel] if pixel in countByColor.keys() else 0) + 1
  return countByColor
