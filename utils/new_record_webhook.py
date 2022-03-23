import textwrap
from dataclasses import dataclass
from textwrap import dedent

from utils.database.user_settings import UserSettings


@dataclass
class NewRecord:
    boss: str
    team_size: str
    boss_mode: str
    time: str
    place: int
    improvement: str
    players: list[str]
    povs: list[str]

    @classmethod
    def from_webhook(cls, embed):
        embed_dict = dict()
        players = list()
        povs = list()
        for field in embed.fields:
            if field.name == 'player':
                players.append(field.value)
            elif field.name == 'place':
                embed_dict['place'] = int(field.value)
            elif field.name == 'pov':
                povs.append(field.value)
            else:
                embed_dict[field.name] = field.value

        return cls(**embed_dict, players=players, povs=povs)

    def set_player_ids(self, users):
        for index, player in enumerate(self.players):
            if user := UserSettings.find_user_by_hiscores_name(player, users):
                self.players[index] = f"<@{user.user_id}>"

    def __str__(self):
        formatted = f"{['1st', '2nd', '3rd'][self.place-1]} place {self.boss_mode} {self.boss} - {self.time} has been achieved by {', '.join(self.players)}"

        if self.place == 1:
            formatted += f" - beating the previous time by {self.improvement}!\n"

        formatted += '\n'.join(self.povs)

        return formatted