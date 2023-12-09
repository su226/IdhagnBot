import json
import os
from typing import Dict

from ..struct.achievement import Achievement
from ..struct.character import PresetCharacter
from ..struct.commons import Weights, parse_weights
from ..struct.event import Event
from ..struct.talent import Talent

_dir = os.path.dirname(os.path.abspath(__file__))
with open(f"{_dir}/age.json") as f:
  AGE: Dict[int, Weights] = {
    int(i["age"]): parse_weights(i["event"]) for i in json.load(f).values()
  }
with open(f"{_dir}/talents.json") as f:
  TALENT: Dict[int, Talent] = {
    (parsed := Talent.parse(talent)).id: parsed for talent in json.load(f).values()
  }
with open(f"{_dir}/events.json") as f:
  EVENT: Dict[int, Event] = {
    (parsed := Event.parse(event)).id: parsed for event in json.load(f).values()
  }
with open(f"{_dir}/achievement.json") as f:
  ACHIEVEMENT: Dict[int, Achievement] = {
    (parsed := Achievement.parse(achievement)).id: parsed for achievement in json.load(f).values()
  }
with open(f"{_dir}/character.json") as f:
  CHARACTER: Dict[int, PresetCharacter] = {
    (parsed := PresetCharacter.parse(character)).id: parsed for character in json.load(f).values()
  }
