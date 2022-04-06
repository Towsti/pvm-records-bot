from dataclasses import dataclass

import interactions

from ..database.user_settings import UserSettings


@dataclass
class NewRecord:
    boss: str
    team_size: str
    boss_mode: str
    time: str
    place: int
    improvement: float
    players: list[str]
    povs: list[str]

    @classmethod
    def from_webhook(cls, embed):
        """Parse new record data from a new record embed webhook

        :param interactions.Embed embed: new record embed (webhook message)
        :return: parsed new record data
        :rtype: NewRecord
        """
        embed_dict = dict()
        players = list()
        povs = list()
        for field in embed.fields:
            if field.name == 'player':
                players.append(field.value)
            elif field.name == 'place':
                embed_dict['place'] = int(field.value)
            elif field.name == 'improvement':
                embed_dict['improvement'] = float(field.value)
            elif field.name == 'pov':
                povs.append(field.value)
            else:
                embed_dict[field.name] = field.value

        return cls(**embed_dict, players=players, povs=povs)

    @staticmethod
    def webhook_sent_embed(embed):
        """Get a embed that can be used to update the original webhook embed to let admins know it has been sent.

        :param interactions.Embed embed: new record embed (webhook message)
        :return: modified new record embed
        :rtype: interactions.Embed
        """
        return interactions.Embed(title=embed.title, fields=embed.fields,
                                  description="Sent :ballot_box_with_check:", color=0x0693E3)

    def set_player_ids(self, users):
        """Change pvm-records.com display names with corresponding discord user names.

        :param list[User] users: users in user settings database
        """
        # todo: manage user ID's of users that aren't in the server anymore
        for index, player in enumerate(self.players):
            if user := UserSettings.find_user_by_display_name(player, users):
                self.players[index] = f"<@{user.user_id}>"

    def __str__(self):
        """String representation, used to format new records message once user ID's are added.

        :return: formatted new record message
        :rtype: str
        """
        place_ordinal = ['1st', '2nd', '3rd'][self.place-1]
        formatted = f"{place_ordinal} place {self.team_size} {self.boss} - {self.boss_mode} - {self.time} has been achieved by {', '.join(self.players)} "

        if self.improvement > 0.1:
            formatted += f" - beating the previous time by {self.improvement} seconds!"

        formatted += '\n'
        formatted += '\n'.join(self.povs)

        return formatted
