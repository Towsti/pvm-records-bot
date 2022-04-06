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
        """Parse request data from a request embed.

        :param interactions.Embed embed: request embed
        :return: parsed request data
        :rtype: RequestData
        """
        result = re.match(r"Channel ID: (\d{18}) \| Message ID: (\d{18})", embed.footer.text)

        fields = dict()
        for field in embed.fields:
            fields[field.name] = field.value

        return cls(int(result.group(1)), int(result.group(2)), fields)

    @staticmethod
    def footer_text(channel_id, message_id):
        """Get the formatted footer text so that it can later be parsed.

        :param int channel_id: request command channel ID
        :param int message_id: request command message ID
        :return: formatted request footer
        :rtype: str
        """
        return f"Channel ID: {channel_id} | Message ID: {message_id}"


class RequestEmbed:
    """Request embed that is used to make a request using a embed.
    Request embeds are generally used when approving requests from a different (admin) channel.
    The request embed stores info about the original message in order to reply to it.
    """

    @staticmethod
    def get_embed(ctx, **embed_kwargs):
        """Create a request embed, add user ID and message ID + normal embed settings.

        :param CommandContext ctx: command context of the original request command
        :param embed_kwargs: additional embed settings such as `description=''`
        :return: request embed
        :rtype: interactions.Embed
        """
        author = interactions.EmbedAuthor(name=ctx.author.user.username, icon_url=ctx.author.user.avatar_url)
        footer = interactions.EmbedFooter(text=RequestData.footer_text(ctx.channel_id, ctx.message.id))
        return interactions.Embed(author=author, footer=footer, color=0xABB8C3, **embed_kwargs)

    @staticmethod
    def approve(embed):
        """get a approve embed from the request embed, generally used to modify the request.

        :param interactions.Embed embed: request embed
        :return: approve embed
        :type: interactions.Embed
        """
        return interactions.Embed(title=embed.title, fields=embed.fields, author=embed.author, footer=embed.footer,
                                  description="Approved :white_check_mark:", color=53380)

    @staticmethod
    def decline(embed):
        """get a decline embed from the request embed, generally used to modify the request embed.

        :param interactions.Embed embed: request embed
        :return: decline embed
        :type: interactions.Embed
        """
        return interactions.Embed(title=embed.title, fields=embed.fields, author=embed.author, footer=embed.footer,
                                  description="Declined :x:", color=15406156)
