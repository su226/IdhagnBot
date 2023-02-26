# pyright: strict
# pylama: ignore=E501 # noqa
from typing import Optional

from ..color_utils import argb_from_lstar, lstar_from_argb
from ..math_utils import clamp, sanitize_degrees
from .cam16 import Cam16
from .viewing_conditions import ViewingConditions

'''
A color system built using CAM16 hue and chroma, and L* from L*a*b*.

Using L* creates a link between the color system, contrast, and thus accessibility. Contrast ratio
depends on relative luminance, or Y in the XYZ color space. L*, or perceptual luminance can be
calculated from Y.

Unlike Y, L* is linear to human perception, allowing trivial creation of accurate color tones.

Unlike contrast ratio, measuring contrast in L* is linear, and simple to calculate. A difference of
40 in HCT tone guarantees a contrast ratio >= 3.0, and a difference of 50 guarantees a contrast
ratio >= 4.5.
'''

_CHROMA_SEARCH_ENDPOINT = 0.4
'''
When the delta between the floor & ceiling of a binary search for maximum chroma at a hue and tone
is less than this, the binary search terminates.
'''

_DE_MAX = 1.0
'''The maximum color distance, in CAM16-UCS, between a requested color and the color returned.'''

_DL_MAX = 0.2
'''The maximum difference between the requested L* and the L* returned.'''

_LIGHTNESS_SEARCH_ENDPOINT = 0.01
'''
When the delta between the floor & ceiling of a binary search for J, lightness in CAM16, is less
than this, the binary search terminates.
'''

def _find_cam_by_j(hue: float, chroma: float, tone: float) -> Optional[Cam16]:
  '''
  :param hue: CAM16 hue
  :param chroma: CAM16 chroma
  :param tone: L*a*b* lightness
  :return: CAM16 instance within error tolerance of the provided dimensions, or null.
  '''
  low = 0.0
  high = 100.0
  mid = 0.0
  bestdL = 1000.0
  bestdE = 1000.0
  bestCam = None
  while abs(low - high) > _LIGHTNESS_SEARCH_ENDPOINT:
    mid = low + (high - low) / 2
    camBeforeClip = Cam16.from_jch(mid, chroma, hue)
    clipped = int(camBeforeClip)
    clippedLstar = lstar_from_argb(clipped)
    dL = abs(tone - clippedLstar)
    if dL < _DL_MAX:
      camClipped = Cam16.from_argb(clipped)
      dE = camClipped.distance(Cam16.from_jch(camClipped.j, camClipped.chroma, hue))
      if dE <= _DE_MAX and dE <= bestdE:
        bestdL = dL
        bestdE = dE
        bestCam = camClipped
    if bestdL == 0 and bestdE == 0:
      break
    if clippedLstar < tone:
      low = mid
    else:
      high = mid
  return bestCam


def _to_argb(hue: float, chroma: float, tone: float, viewing_conditions: ViewingConditions = ViewingConditions.DEFAULT) -> int:
  '''
  :param hue: a number, in degrees, representing ex. red, orange, yellow, etc.
              Ranges from 0 <= hue < 360.
  :param chroma: Informally, colorfulness. Ranges from 0 to roughly 150. Like all perceptually
                 accurate color systems, chroma has a different maximum for any given hue and tone,
                 so the color returned may be lower than the requested chroma.
  :param tone: Lightness. Ranges from 0 to 100.
  :param viewing_conditions: Information about the environment where the color was observed.
  :return: ARGB representation of a color in default viewing conditions
  '''
  hue = sanitize_degrees(hue)
  tone = clamp(0.0, 100.0, tone)
  if chroma < 1.0 or round(tone) <= 0.0 or round(tone) >= 100.0:
    return argb_from_lstar(tone)

  hue = sanitize_degrees(hue)
  high = chroma
  mid = chroma
  low = 0.0
  isFirstLoop = True
  answer = None
  while abs(low - high) >= _CHROMA_SEARCH_ENDPOINT:
    possibleAnswer = _find_cam_by_j(hue, mid, tone)
    if isFirstLoop:
      if possibleAnswer is not None:
        return possibleAnswer.to_argb(viewing_conditions)
      else:
        isFirstLoop = False
        mid = low + (high - low) / 2.0
        continue
    if possibleAnswer is None:
      high = mid
    else:
      answer = possibleAnswer
      low = mid
    mid = low + (high - low) / 2.0
  if answer is None:
    return argb_from_lstar(tone)
  return answer.to_argb(viewing_conditions)


class Hct:
  '''
  HCT, hue, chroma, and tone. A color system that provides a perceptually accurate color
  measurement system that can also accurately render what colors will appear as in different
  lighting environments.
  '''

  def __init__(self, hue: float, chroma: float, tone: float) -> None:
    self._set_argb(_to_argb(hue, chroma, tone))

  @staticmethod
  def from_argb(argb: int) -> "Hct":
    '''
    :param argb: ARGB representation of a color.
    :return: HCT representation of a color in default viewing conditions
    '''
    cam = Cam16.from_argb(argb)
    tone = lstar_from_argb(argb)
    return Hct(cam.hue, cam.chroma, tone)

  def __int__(self) -> int:
    return _to_argb(self._hue, self._chroma, self._tone)

  @property
  def hue(self) -> float:
    '''
    A number, in degrees, representing ex. red, orange, yellow, etc. Ranges from 0 <= hue < 360.
    '''
    return self._hue

  @hue.setter
  def hue(self, value: float) -> None:
    '''
    :param value: 0 <= hue < 360; invalid values are corrected.
    Chroma may decrease because chroma has a different maximum for any given hue and tone.
    '''
    self._set_argb(_to_argb(sanitize_degrees(value), self._chroma, self._tone))

  @property
  def chroma(self) -> float:
    return self._chroma

  @chroma.setter
  def chroma(self, value: float) -> None:
    '''
    :param value: 0 <= chroma < ?
    Chroma may decrease because chroma has a different maximum for any given hue and tone.
    '''
    self._set_argb(_to_argb(self._hue, value, self._tone))

  @property
  def tone(self) -> float:
    '''Lightness. Ranges from 0 to 100.'''
    return self._tone

  @tone.setter
  def tone(self, value: float) -> None:
    '''
    :param value: 0 <= tone <= 100; invalid valids are corrected.
    Chroma may decrease because chroma has a different maximum for any given hue and tone.
    '''
    self._set_argb(_to_argb(self._hue, self._chroma, value))

  def _set_argb(self, argb: int) -> None:
    cam = Cam16.from_argb(argb)
    self._hue = cam.hue
    self._chroma = cam.chroma
    self._tone = lstar_from_argb(argb)
