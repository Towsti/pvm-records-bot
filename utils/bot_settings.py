import os
from dataclasses import dataclass
import json

from dotenv import load_dotenv
from dataclasses_json import DataClassJsonMixin


load_dotenv()


@dataclass(frozen=True)
class Roles(DataClassJsonMixin):
    hiscores_leader: int
    first_place_holder: int
    second_place_holder: int
    third_place_holder: int
    scores: list[int, int]


@dataclass(frozen=True)
class Hiscores(DataClassJsonMixin):
    approval_role: int
    roles: Roles


@dataclass(frozen=True)
class BotSettings(DataClassJsonMixin):
    guild: int
    hiscores: Hiscores


with open(os.environ.get('BOT_SETTINGS', 'bot_settings.json'), 'r') as file:
    BOT_SETTINGS = BotSettings.from_dict(json.load(file))