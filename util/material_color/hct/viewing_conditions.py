# pyright: strict
# pylama: ignore=E501 # noqa
import math
from dataclasses import dataclass
from typing import ClassVar

from ..color_utils import WHITE_POINT_D65, Vec3f, y_from_lstar
from ..math_utils import lerp


@dataclass
class ViewingConditions:
  '''
  In traditional color spaces, a color can be identified solely by the observer's measurement of
  the color. Color appearance models such as CAM16 also use information about the environment where
  the color was observed, known as the viewing conditions.

  For example, white under the traditional assumption of a midday sun white point is accurately
  measured as a slightly chromatic blue by CAM16. (roughly, hue 203, chroma 3, lightness 100)

  This class caches intermediate values of the CAM16 conversion process that depend only on viewing
  conditions, enabling speed ups.

  Parameters are intermediate values of the CAM16 conversion process. Their names are shorthand for
  technical color science terminology, this class would not benefit from documenting them
  individually. A brief overview is available in the CAM16 specification, and a complete overview
  requires a color science textbook, such as Fairchild's Color Appearance Models.
  '''

  DEFAULT: ClassVar["ViewingConditions"]
  '''sRGB-like viewing conditions.'''

  n: float
  aw: float
  nbb: float
  ncb: float
  c: float
  nc: float
  rgbD: Vec3f
  fl: float
  fLRoot: float
  z: float

  @staticmethod
  def make(white_point: Vec3f = WHITE_POINT_D65, adapting_luminance: float = (200.0 / math.pi) * y_from_lstar(50.0) / 100.0, background_lstar: float = 50.0, surround: float = 2.0, discounting_illuminant: bool = False) -> "ViewingConditions":
    '''
    Create ViewingConditions from a simple, physically relevant, set of
    parameters.

    :param white_point: White point, measured in the XYZ color space. default = D65, or sunny day
                        afternoon
    :param adapting_luminance: The luminance of the adapting field. Informally, how bright it is in
                               the room where the color is viewed. Can be calculated from lux by
                               multiplying lux by 0.0586. default = 11.72, or 200 lux.
    :param background_lstar: The lightness of the area surrounding the color. measured by L* in
                             L*a*b*. default = 50.0
    :param surround: A general description of the lighting surrounding the color. 0 is pitch dark,
                     like watching a movie in a theater. 1.0 is a dimly light room, like watching
                     TV at home at night. 2.0 means there is no difference between the lighting on
                     the color and around it. default = 2.0
    :param discounting_illuminant: Whether the eye accounts for the tint of the ambient lighting,
                                   such as knowing an apple is still red in green light.
                                   default = false, the eye does not perform this process on
                                   self-luminous objects like displays.
    '''
    xyz = white_point
    rW = xyz[0] * 0.401288 + xyz[1] * 0.650173 + xyz[2] * -0.051461
    gW = xyz[0] * -0.250268 + xyz[1] * 1.204414 + xyz[2] * 0.045854
    bW = xyz[0] * -0.002079 + xyz[1] * 0.048952 + xyz[2] * 0.953127
    f = 0.8 + surround / 10.0
    c = lerp(0.59, 0.69, (f - 0.9) * 10.0) if f >= 0.9 else lerp(0.525, 0.59, (f - 0.8) * 10.0)
    d = 1.0 if discounting_illuminant else f * (1.0 - (1.0 / 3.6) * math.exp((-adapting_luminance - 42.0) / 92.0))
    d = 1.0 if d > 1.0 else 0.0 if d < 0.0 else d
    nc = f
    rgbD = (
      d * (100.0 / rW) + 1.0 - d,
      d * (100.0 / gW) + 1.0 - d,
      d * (100.0 / bW) + 1.0 - d,
    )
    k = 1.0 / (5.0 * adapting_luminance + 1.0)
    k4 = k * k * k * k
    k4F = 1.0 - k4
    fl = k4 * adapting_luminance + 0.1 * k4F * k4F * ((5.0 * adapting_luminance)**(1. / 3))
    n = y_from_lstar(background_lstar) / white_point[1]
    z = 1.48 + math.sqrt(n)
    nbb = 0.725 / pow(n, 0.2)
    ncb = nbb
    rgbAFactors = (
      ((fl * rgbD[0] * rW) / 100.0) ** 0.42,
      ((fl * rgbD[1] * gW) / 100.0) ** 0.42,
      ((fl * rgbD[2] * bW) / 100.0) ** 0.42,
    )
    rgbA = (
      (400.0 * rgbAFactors[0]) / (rgbAFactors[0] + 27.13),
      (400.0 * rgbAFactors[1]) / (rgbAFactors[1] + 27.13),
      (400.0 * rgbAFactors[2]) / (rgbAFactors[2] + 27.13),
    )
    aw = (2.0 * rgbA[0] + rgbA[1] + 0.05 * rgbA[2]) * nbb
    return ViewingConditions(n, aw, nbb, ncb, c, nc, rgbD, fl, fl ** 0.25, z)

ViewingConditions.DEFAULT = ViewingConditions.make()
