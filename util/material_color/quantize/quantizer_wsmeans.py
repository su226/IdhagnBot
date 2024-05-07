# pyright: strict
# ruff: noqa: E501
import math
import random
from dataclasses import dataclass
from typing import Iterable, List, OrderedDict

from ..color_utils import argb_from_lab, lab_from_argb
from ..math_utils import Vec3f, point_distance

'''
An image quantizer that improves on the speed of a standard K-Means algorithm by implementing
several optimizations, including deduping identical pixels and a triangle inequality rule that
reduces the number of comparisons needed to identify which cluster a point should be moved to.

Wsmeans stands for Weighted Square Means.

This algorithm was designed by M. Emre Celebi, and was found in their 2011 paper, Improving the
Performance of K-Means for Color Quantization.
https://arxiv.org/abs/1101.0395
'''

_MAX_ITERATIONS = 10
_MIN_MOVEMENT_DISTANCE = 3.0


@dataclass
class _DistanceAndIndex:
  '''A wrapper for maintaining a table of distances between K-Means clusters.'''
  distance: float = -1
  index: int = -1


def quantize(input_pixels: Iterable[int], starting_clusters: List[int], max_colors: int) -> OrderedDict[int, int]:
  '''
  :param input_pixels: Colors in ARGB format.
  :param starting_clusters: Defines the initial state of the quantizer. Passing an empty array is
                            fine, the implementation will create its own initial state that leads
                            to reproducible results for the same inputs. Passing an array that is
                            the result of Wu quantization leads to higher quality results.
  :param max_colors: The number of colors to divide the image into. A lower number of colors may be
                     returned.
  :return: Colors in ARGB format.
  '''
  random.seed(69)
  pixelToCount = OrderedDict[int, int]()
  points: List[Vec3f] = []
  pixels: List[int] = []
  pointCount = 0
  for inputPixel in input_pixels:
    if inputPixel not in pixelToCount:
      pointCount += 1
      points.append(lab_from_argb(inputPixel))
      pixels.append(inputPixel)
      pixelToCount[inputPixel] = 1
    else:
      pixelToCount[inputPixel] = pixelToCount[inputPixel] + 1
  counts: List[int] = []
  for i in range(pointCount):
    pixel = pixels[i]
    if pixel in pixelToCount:
      counts.append(pixelToCount[pixel])
  clusterCount = min(max_colors, pointCount)
  if starting_clusters:
    clusterCount = min(clusterCount, len(starting_clusters))
  clusters: List[Vec3f] = []
  for cluster in starting_clusters:
    clusters.append(lab_from_argb(cluster))
  additionalClustersNeeded = clusterCount - len(clusters)
  if not starting_clusters and additionalClustersNeeded > 0:
    for i in range(additionalClustersNeeded):
      l = random.uniform(0, 1) * 100.0
      a = random.uniform(0, 1) * (100.0 - (-100.0) + 1) + -100
      b = random.uniform(0, 1) * (100.0 - (-100.0) + 1) + -100
      clusters.append((l, a, b))
  clusterIndices: List[int] = []
  for i in range(pointCount):
    clusterIndices.append(math.floor(random.uniform(0, 1) * clusterCount))
  indexMatrix: List[List[int]] = []
  for i in range(clusterCount):
    indexMatrix.append([])
    for j in range(clusterCount):
      indexMatrix[i].append(0)
  distanceToIndexMatrix: List[List[_DistanceAndIndex]] = []
  for i in range(clusterCount):
    distanceToIndexMatrix.append([])
    for j in range(clusterCount):
      distanceToIndexMatrix[i].append(_DistanceAndIndex())
  pixelCountSums: List[int] = []
  for i in range(clusterCount):
    pixelCountSums.append(0)
  for iteration in range(_MAX_ITERATIONS):
    for i in range(clusterCount):
      for j in range(i + 1, clusterCount):
        distance = point_distance(clusters[i], clusters[j])
        distanceToIndexMatrix[j][i].distance = distance
        distanceToIndexMatrix[j][i].index = i
        distanceToIndexMatrix[i][j].distance = distance
        distanceToIndexMatrix[i][j].index = j
      for j in range(clusterCount):
        indexMatrix[i][j] = distanceToIndexMatrix[i][j].index
    pointsMoved = 0
    for i in range(pointCount):
      point = points[i]
      previousClusterIndex = clusterIndices[i]
      previousCluster = clusters[previousClusterIndex]
      previousDistance = point_distance(point, previousCluster)
      minimumDistance = previousDistance
      newClusterIndex = -1
      for j in range(clusterCount):
        if distanceToIndexMatrix[previousClusterIndex][j].distance >= 4 * previousDistance:
          continue
        distance = point_distance(point, clusters[j])
        if distance < minimumDistance:
          minimumDistance = distance
          newClusterIndex = j
      if newClusterIndex != -1:
        distanceChange = abs((math.sqrt(minimumDistance) - math.sqrt(previousDistance)))
        if distanceChange > _MIN_MOVEMENT_DISTANCE:
          pointsMoved += 1
          clusterIndices[i] = newClusterIndex
    if pointsMoved == 0 and iteration != 0:
      break
    componentASums: List[float] = [0] * clusterCount
    componentBSums: List[float] = [0] * clusterCount
    componentCSums: List[float] = [0] * clusterCount
    for i in range(clusterCount):
      pixelCountSums[i] = 0
    for i in range(pointCount):
      clusterIndex = clusterIndices[i]
      point = points[i]
      count = counts[i]
      pixelCountSums[clusterIndex] += count
      componentASums[clusterIndex] += point[0] * count
      componentBSums[clusterIndex] += point[1] * count
      componentCSums[clusterIndex] += point[2] * count
    for i in range(clusterCount):
      count = pixelCountSums[i]
      if count == 0:
        clusters[i] = (0, 0, 0)
        continue
      a = componentASums[i] / count
      b = componentBSums[i] / count
      c = componentCSums[i] / count
      clusters[i] = (a, b, c)
  argbToPopulation = OrderedDict[int, int]()
  for i in range(clusterCount):
    count = pixelCountSums[i]
    if count == 0:
      continue
    possibleNewCluster = argb_from_lab(*clusters[i])
    if possibleNewCluster in argbToPopulation:
      continue
    argbToPopulation[possibleNewCluster] = count
  return argbToPopulation
