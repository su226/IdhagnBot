# pyright: strict
# ruff: noqa: E501
from typing import List, Mapping, OrderedDict

from .color_utils import lstar_from_argb
from .hct.cam16 import Cam16
from .math_utils import difference_degrees, sanitize_degrees

'''
Given a large set of colors, remove colors that are unsuitable for a UI theme, and rank the rest
based on suitability.

Enables use of a high cluster count for image quantization, thus ensuring colors aren't muddied,
while curating the high cluster count to a much smaller number of appropriate choices.
'''

_TARGET_CHROMA = 48.0
_WEIGHT_PROPORTION = 0.7
_WEIGHT_CHROMA_ABOVE = 0.3
_WEIGHT_CHROMA_BELOW = 0.1
_CUTOFF_CHROMA = 15.0
_CUTOFF_TONE = 10.0
_CUTOFF_EXCITED_PROPORTION = 0.01

def _filterColors(colors_to_excited_proportion: Mapping[int, float], colors_to_cam: Mapping[int, Cam16]) -> List[int]:
  filtered: List[int] = []
  for color, cam in colors_to_cam.items():
    proportion = colors_to_excited_proportion[color]
    if cam.chroma >= _CUTOFF_CHROMA and lstar_from_argb(color) >= _CUTOFF_TONE and proportion >= _CUTOFF_EXCITED_PROPORTION:
      filtered.append(color)
  return filtered

@staticmethod
def score(colors_to_population: Mapping[int, int]) -> List[int]:
  '''
  Given a map with keys of colors and values of how often the color appears, rank the colors based
  on suitability for being used for a UI theme.

  :param colors_to_population: map with keys of colors and values of how often the color appears,
                               usually from a source image.
  :return: Colors sorted by suitability for a UI theme. The most suitable color is the first item,
           the least suitable is the last. There will always be at least one color returned. If all
           the input colors were not suitable for a theme, a default fallback color will be
           provided, Google Blue.
  '''
  # Determine the total count of all colors.
  populationSum = 0
  for population in colors_to_population.values():
    populationSum += population
  # Turn the count of each color into a proportion by dividing by the total
  # count. Also, fill a cache of CAM16 colors representing each color, and
  # record the proportion of colors for each CAM16 hue.
  colorsToProportion = OrderedDict[int, float]()
  colorsToCam = OrderedDict[int, Cam16]()
  hueProportions = [0.0] * 361
  for color, population in colors_to_population.items():
    proportion = population / populationSum
    colorsToProportion[color] = proportion
    cam = Cam16.from_argb(color)
    colorsToCam[color] = cam
    hue = round(cam.hue)
    hueProportions[hue] += proportion
  # Determine the proportion of the colors around each color, by summing the
  # proportions around each color's hue.
  colorsToExcitedProportion = OrderedDict[int, float]()
  for color, cam in colorsToCam.items():
    hue = round(cam.hue)
    excitedProportion = 0
    for i in range((hue - 15), (hue + 15)):
      neighborHue = sanitize_degrees(i)
      excitedProportion += hueProportions[neighborHue]
    colorsToExcitedProportion[color] = excitedProportion
  # Score the colors by their proportion, as well as how chromatic they are.
  colorsToScore = OrderedDict[int, float]()
  for color, cam in colorsToCam.items():
    proportion = colorsToExcitedProportion[color]
    proportionScore = proportion * 100.0 * _WEIGHT_PROPORTION
    chromaWeight = _WEIGHT_CHROMA_BELOW if cam.chroma < _TARGET_CHROMA else _WEIGHT_CHROMA_ABOVE
    chromaScore = (cam.chroma - _TARGET_CHROMA) * chromaWeight
    score = proportionScore + chromaScore
    colorsToScore[color] = score
  # Remove colors that are unsuitable, ex. very dark or unchromatic colors.
  # Also, remove colors that are very similar in hue.
  filteredColors = _filterColors(colorsToExcitedProportion, colorsToCam)
  dedupedColorsToScore = OrderedDict[int, float]()
  for color in filteredColors:
    duplicateHue = False
    hue = colorsToCam[color].hue
    for alreadyChosenColor in dedupedColorsToScore:
      alreadyChosenHue = colorsToCam[alreadyChosenColor].hue
      if difference_degrees(hue, alreadyChosenHue) < 15:
        duplicateHue = True
        break
    if duplicateHue:
      continue
    dedupedColorsToScore[color] = colorsToScore[color]
  # Ensure the list of colors returned is sorted such that the first in the
  # list is the most suitable, and the last is the least suitable.
  colorsByScoreDescending = list(dedupedColorsToScore.items())
  colorsByScoreDescending.sort(reverse=True, key=lambda x: x[1])
  answer = [x[0] for x in colorsByScoreDescending]
  # Ensure that at least one color is returned.
  if len(answer) == 0:
    answer.append(0xff4285f4)  # Google Blue
  return answer
