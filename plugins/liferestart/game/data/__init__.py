from ..struct.commons import Weights, parse_weights
from ..struct.character import Character
from ..struct.talent import Talent
from ..struct.achievement import Achievement
from ..struct.event import Event
import json
import os

_dir = os.path.dirname(os.path.abspath(__file__))
with open(f"{_dir}/age.json") as f:
  AGE: dict[int, Weights] = {int(i["age"]): parse_weights(i["event"]) for i in json.load(f).values()}
with open(f"{_dir}/talents.json") as f:
  TALENT: dict[int, Talent] = {talent.id: talent for talent in map(Talent.parse, json.load(f).values())}
with open(f"{_dir}/events.json") as f:
  EVENT: dict[int, Event] = {event.id: event for event in map(Event.parse, json.load(f).values())}
with open(f"{_dir}/achievement.json") as f:
  ACHIEVEMENT: dict[int, Achievement] = {achievement.id: achievement for achievement in map(Achievement.parse, json.load(f).values())}
with open(f"{_dir}/character.json") as f:
  CHARACTER: dict[int, Character] = {character.id: character for character in map(Character.parse, json.load(f).values())}
