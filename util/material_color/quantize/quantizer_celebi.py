# pyright: strict
from typing import List, OrderedDict

from . import quantizer_wsmeans, quantizer_wu

'''
An image quantizer that improves on the quality of a standard K-Means algorithm by setting the
K-Means initial state to the output of a Wu quantizer, instead of random centroids. Improves on
speed by several optimizations, as implemented in Wsmeans, or Weighted Square Means, K-Means with
those optimizations.

This algorithm was designed by M. Emre Celebi, and was found in their 2011 paper, Improving the
Performance of K-Means for Color Quantization.
https://arxiv.org/abs/1101.0395
'''

def quantize(pixels: List[int], max_colors: int) -> OrderedDict[int, int]:
  '''
  :param pixels: Colors in ARGB format.
  :param max_colors: The number of colors to divide the image into. A lower number of colors may be
                     returned.
  :return: Map with keys of colors in ARGB format, and values of number of pixels in the original
           image that correspond to the color in the quantized image.
  '''
  return quantizer_wsmeans.quantize(pixels, quantizer_wu.quantize(pixels, max_colors), max_colors)
