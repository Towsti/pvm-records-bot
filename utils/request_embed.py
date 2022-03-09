import re
from dataclasses import dataclass

import interactions


@dataclass(frozen=True)
class RequestData:
    channel_id: int
    message_id: int
    fields: dict

    @classmethod
    def from_embed(cls, embed):
        result = re.match(r"Channel ID: (\d{18}) \| Message ID: (\d{18})", embed.footer.text)

        fields = dict()
        for field in embed.fields:
            fields[field.name] = field.value

        return cls(int(result.group(1)), int(result.group(2)), fields)

    @staticmethod
    def footer_text(channel_id, message_id):
        return f"Channel ID: {channel_id} | Message ID: {message_id}"


class RequestEmbed:
    @staticmethod
    def get_embed(ctx, **embed_kwargs):
        author = interactions.EmbedAuthor(name=ctx.author.user.username, icon_url=ctx.author.user.avatar_url)
        footer = interactions.EmbedFooter(text=RequestData.footer_text(ctx.channel_id, ctx.message.id))

        return interactions.Embed(author=author, footer=footer, **embed_kwargs)
