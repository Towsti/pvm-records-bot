import logging

import interactions
from interactions.ext.enhanced.components import ActionRow, Button, TextInput, Modal

from utils.database.user_settings import UserSettings, User
from utils.bot_settings import BOT_SETTINGS
from utils.embeds.request import RequestEmbed
from utils.embeds.link_request import LinkRequest
from utils.pvm_records.hiscores import Hiscores


logger = logging.getLogger(__name__)


class UserConfigurationBot(interactions.Extension):
    def __init__(self, client):
        self.client = client
        self.admin_channel = None
        self.user_settings = UserSettings()
        self.hiscores = Hiscores()

    @interactions.extension_listener()
    async def on_guild_create(self, ctx):
        response_json = await ctx._client.get_channel(BOT_SETTINGS.admin_channel)
        self.admin_channel = interactions.Channel(**response_json, _client=ctx._client)

    @interactions.extension_command()
    async def link_name(self, ctx):
        """Link your discord to a pvm-records.com display name."""
        modal = Modal(
            title="Link User",
            custom_id="link_request_modal",
            components=[
                TextInput(
                    label="pvm-records.com display name",
                    custom_id="display_name",
                    min_length=1
                ),
                TextInput(
                    label="Screenshot of you saying your name in game",
                    custom_id="proof",
                    placeholder="https://imgur.com/12Djsd2",
                    required=False
                ),
            ]
        )
        await ctx.popup(modal)

    @interactions.extension_modal("link_request_modal")
    async def link_request_modal_response(self, ctx, name, proof):
        if self.user_settings.get_user_by_display_name(name):
            return await ctx.send(f"{name} already linked.", ephemeral=True)

        await ctx.send(f"Verification request for {name} - awaiting approval.")
        await self.admin_channel.send(
            embeds=LinkRequest.create_embed(ctx, name, proof, await self.__on_hiscore_message(name)),
            components=ActionRow(
                Button(interactions.ButtonStyle.SUCCESS, "Approve", custom_id="approve_button"),
                Button(interactions.ButtonStyle.DANGER, "Decline", custom_id="decline_button")))

    @interactions.extension_component("approve_button")
    async def approved(self, ctx):
        request = LinkRequest.from_embed(ctx.message.embeds[0])

        await self.user_settings.update(User(request.user_id, request.display_name))

        await self.__reply_request_message(request.channel_id, request.message_id,
                                           f"<@{request.user_id}> Approved :white_check_mark:")
        await ctx.edit(embeds=RequestEmbed.approve(ctx.message.embeds[0]), components=None)

    @interactions.extension_component("decline_button")
    async def declined(self, ctx):
        request = LinkRequest.from_embed(ctx.message.embeds[0])

        await self.__reply_request_message(request.channel_id, request.message_id,
                                           f"<@{request.user_id}> Declined :x:")
        await ctx.edit(embeds=RequestEmbed.decline(ctx.message.embeds[0]), components=None)

    @interactions.extension_command()
    async def unlink_name(self, ctx):
        """Unlink your discord from pvm-records.com and clear all roles."""
        if user := self.user_settings.get_user_by_id(int(ctx.author.id)):
            await self.user_settings.delete(user.user_id)
            await ctx.send(f"Unlinked {user.display_name}.")
        else:
            await ctx.send(f"Already unlinked.", ephemeral=True)

    async def __reply_request_message(self, channel_id, message_id, content):
        await self.client._http.send_message(channel_id, content, message_reference={'message_id': message_id})

    async def __on_hiscore_message(self, name):
        if not await self.hiscores.refresh():
            return ":warning: Failed to load hiscores"

        if self.hiscores.entry_exists(self.hiscores.get_entry_by_name(name)):
            message = ''
        else:
            message = f":warning: Couldn't find {name} on hiscores"

        return message

def setup(client):
    UserConfigurationBot(client)
