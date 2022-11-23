import json
import os
from typing import Dict

from ..struct.achievement import Achievement
from ..struct.character import Character
from ..struct.commons import Weights, parse_weights
from ..struct.event import Event
from ..struct.talent import Talent

_dir = os.path.dirname(os.path.abspath(__file__))
with open(f"{_dir}/age.json") as f:
  AGE: Dict[int, Weights] = {
    int(i["age"]): parse_weights(i["event"]) for i in json.load(f).values()}
with open(f"{_dir}/talents.json") as f:
  TALENT: Dict[int, Talent] = {
    talent.id: talent for talent in map(Talent.parse, json.load(f).values())}
with open(f"{_dir}/events.json") as f:
  EVENT: Dict[int, Event] = {
    event.id: event for event in map(Event.parse, json.load(f).values())}
with open(f"{_dir}/achievement.json") as f:
  ACHIEVEMENT: Dict[int, Achievement] = {
    achievement.id: achievement for achievement in map(Achievement.parse, json.load(f).values())}
with open(f"{_dir}/character.json") as f:
  CHARACTER: Dict[int, Character] = {
    character.id: character for character in map(Character.parse, json.load(f).values())}
