import os
from dataclasses import dataclass
import json

from dotenv import load_dotenv
from dataclasses_json import DataClassJsonMixin


load_dotenv()


@dataclass(frozen=True)
class HiscoreRoles(DataClassJsonMixin):
    hiscores_leader: int
    first_place_holder: int
    second_place_holder: int
    third_place_holder: int
    scores: list[int, int]


@dataclass(frozen=True)
class NewRecord(DataClassJsonMixin):
    webhook: int
    channel: int


@dataclass(frozen=True)
class BotSettings(DataClassJsonMixin):
    guild: int
    admin_channel: int
    admin_role: int
    new_record: NewRecord
    hiscore_roles: HiscoreRoles


# load bot settings, use versioned bot_settings.json by default
with open(os.environ.get('BOT_SETTINGS', 'bot_settings.json'), 'r') as file:
    BOT_SETTINGS = BotSettings.from_dict(json.load(file))
