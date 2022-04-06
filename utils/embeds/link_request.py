from dataclasses import dataclass
import re

from interactions import EmbedField

from .request import RequestEmbed, RequestData


class FieldNames:
    user_id = "User ID"
    record_display_name = "Record display name"
    proof = "Proof"


@dataclass(frozen=True)
class LinkRequest(RequestData):
    _field_names = FieldNames()
    user_id: int
    display_name: str

    @classmethod
    def from_embed(cls, embed):
        """Parse link request data from a request embed.

        :param interactions.Embed embed: request embed
        :return: parsed request data
        :rtype: LinkRequest
        """
        request = RequestData.from_embed(embed)
        result = re.match(r"<@(\d{18})>", request.fields[LinkRequest._field_names.user_id])
        return cls(**request.__dict__,
                   user_id=int(result.group(1)),
                   display_name=request.fields[LinkRequest._field_names.record_display_name])

    @staticmethod
    def create_embed(ctx, name, proof=None, description=''):
        """Create link request embed.

        :param interactions.CommandContext ctx: command context
        :param str name: pvm-records.com display name
        :param str proof: optional proof message
        :param str description: description indicating if the display name is on pvm-records.com
        :return: request embed
        :rtype: interactions.Embed
        """
        fields = [
            EmbedField(
                name=LinkRequest._field_names.user_id,
                value=str(ctx.author.mention),
                inline=True
            ),
            EmbedField(
                name=LinkRequest._field_names.record_display_name,
                value=name,
                inline=True
            )
        ]
        if proof:
            fields.append(EmbedField(
                name=LinkRequest._field_names.proof,
                value=proof,
                inline=False
            ))
        return RequestEmbed.get_embed(ctx, title="Link name request", fields=fields, description=description)
