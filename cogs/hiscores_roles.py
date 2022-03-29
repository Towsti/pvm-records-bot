import os
import re
from dataclasses import dataclass
import logging

import interactions
from interactions.ext.enhanced import EnhancedOption
from interactions.ext.enhanced.components import ActionRow
from interactions.ext.enhanced.components import Button

from utils.database.user_settings import UserSettings, User
from utils.pvm_records.hiscores import Hiscores, Entry
from utils.bot_settings import BOT_SETTINGS
from utils.request_embed import RequestData, RequestEmbed
from utils.new_record_webhook import NewRecord


logger = logging.getLogger(__name__)
WEBHOOK_TOKEN = os.getenv('WEBHOOK_TOKEN')


@dataclass(frozen=True)
class HiscoreRequest(RequestData):
    USER_ID_FIELD = "User ID"
    HISCORES_NAME_FIELD = "Hiscore name"

    user_id: int
    hiscores_name: str

    @classmethod
    def from_embed(cls, embed):
        request = RequestData.from_embed(embed)
        result = re.match(r"<@(\d{18})>", request.fields[HiscoreRequest.USER_ID_FIELD])
        return cls(**request.__dict__,
                   user_id=int(result.group(1)),
                   hiscores_name=request.fields[HiscoreRequest.HISCORES_NAME_FIELD])

    @staticmethod
    def create_embed(ctx, name):
        fields = [
            interactions.EmbedField(
                name=HiscoreRequest.USER_ID_FIELD,
                value=str(ctx.author.mention),
                inline=True
            ),
            interactions.EmbedField(
                name=HiscoreRequest.HISCORES_NAME_FIELD,
                value=name,
                inline=True
            )
        ]
        return RequestEmbed.get_embed(ctx, title="Hiscore roles request", fields=fields)


class RoleUpdater:
    def __init__(self, http_client):
        self.__http = http_client
        self.__guild = BOT_SETTINGS.guild
        self.__roles = BOT_SETTINGS.hiscore_roles

    async def clear_roles(self, member):
        logger.info(f"clearing roles for {member.user.username}")
        for role, eligible in Entry.empty().get_eligible_roles(self.__roles):
           await self.__update_role(member, role, eligible)

    async def update_roles(self, member, hiscores_entry):
        for role, eligible in hiscores_entry.get_eligible_roles(self.__roles):
            await self.__update_role(member, role, eligible)

    async def __update_role(self, member, role, eligible):
        if eligible:
            if role not in member.roles:
                await self.__http.add_member_role(self.__guild, member.id, role)
        else:
            if role in member.roles:
                await self.__http.remove_member_role(self.__guild, member.id, role)


class HiscoresRolesBot(interactions.Extension):
    def __init__(self, client):
        self.client = client
        self.user_settings = UserSettings()
        self.hiscores = Hiscores()
        self.role_updater = RoleUpdater(self.client._http)

    @interactions.extension_command()
    async def experimental_update_roles(self, ctx):
        """Experimental implementation of update-roles"""
        if not await self.hiscores.refresh():
            return await ctx.send("Failed to load hiscores, try again later.", ephemeral=True)

        await ctx.defer()

        configured_users = self.user_settings.get_users()

        members = await self.client._http.get_list_of_members(BOT_SETTINGS.guild, 1000)
        for member_dict in members:
            member = interactions.Member(**member_dict)
            if not member.roles:
                # member.roles attribute now set to None instead of [] when there are no roles
                member.roles = list()
            if user_settings := UserSettings.find_user_by_id(int(member.id), configured_users):
                entry = self.hiscores.get_entry_by_name(user_settings.hiscores_name)
                await self.role_updater.update_roles(member, entry)
            else:
                await self.role_updater.clear_roles(member)

        await ctx.send("done", ephemeral=True)


    # @interactions.extension_listener()
    # async def on_guild_create(self, guild):
    #     configured_users = self.user_settings.get_users()
    #     for member in guild.members:
    #         if not UserSettings.find_user_by_id(int(member.id), configured_users):
    #             await self.role_updater.clear_roles(member)
    #     logger.info("bot ready")

    @interactions.extension_listener()
    async def on_message_create(self, message):
        if int(message.author.id) == BOT_SETTINGS.new_record.webhook:
            await self.__send_new_record(message)
            if await self.hiscores.refresh():
                await self.__update_all_hiscore_roles()
                await self.client._http.send_message(BOT_SETTINGS.admin_channel,
                                                     "Roles updated :arrows_counterclockwise:")

    @interactions.extension_message_command()
    async def resend_new_record(self, ctx):
        if BOT_SETTINGS.admin_role not in ctx.author.roles:
            return await ctx.send(f"Only those with <@&{BOT_SETTINGS.admin_role}> are allowed to update roles.",
                                  ephemeral=True)

        if int(ctx.target.author.id) != BOT_SETTINGS.new_record.webhook:
            return await ctx.send("this is not a new record webhook", ephemeral=True)

        await self.__send_new_record(ctx.target)

        if not await self.hiscores.refresh():
            return await ctx.send("Failed to load hiscores, try again later.", ephemeral=True)

        await ctx.defer()

        await self.__update_all_hiscore_roles()
        await ctx.send("Roles updated :arrows_counterclockwise:")

    async def __send_new_record(self, message):
        embed = message.embeds[0]

        new_record = NewRecord.from_webhook(embed)
        configured_users = self.user_settings.get_users()
        new_record.set_player_ids(configured_users)

        await self.client._http.send_message(BOT_SETTINGS.new_record.channel, str(new_record))
        await self.client._http.edit_webhook_message(message.webhook_id, WEBHOOK_TOKEN, message.id,
                                                     {'embeds': [NewRecord.webhook_sent_embed(embed)._json]})

    @interactions.extension_command()
    async def enable_hiscores_roles(self, ctx, name: EnhancedOption(str, "pvm-records.com/hiscores name")):
        """Enable discord roles based on pvm-records.com/hiscores."""
        if self.user_settings.get_user_by_hiscores_name(name):
            return await ctx.send(f"Hiscore roles already enabled for {name}.", ephemeral=True)

        admin_channel = interactions.Channel(**await ctx.client.get_channel(BOT_SETTINGS.admin_channel),
                                             _client=ctx.client)

        await ctx.send(f"Awaiting approval to enable hiscore roles for {name}.")
        await admin_channel.send(
            embeds=HiscoreRequest.create_embed(ctx, name),
            components=ActionRow(
                Button(interactions.ButtonStyle.SUCCESS, "Approve", custom_id="approve"),
                Button(interactions.ButtonStyle.DANGER, "Decline", custom_id="decline")))

    @interactions.extension_component("approve")
    async def approved(self, ctx):
        if not await self.hiscores.refresh():
            return await ctx.send("Failed to load hiscores, try again later.", ephemeral=True)

        request = HiscoreRequest.from_embed(ctx.message.embeds[0])
        request_message = await self.__get_original_request_message(ctx, request.channel_id, request.message_id)

        await self.__enable_hiscore_roles(request.user_id, request.hiscores_name)

        await request_message.reply(f"<@{request.user_id}> Approved :white_check_mark:")
        await ctx.edit(embeds=RequestEmbed.approve(ctx.message.embeds[0]), components=None)

    @interactions.extension_component("decline")
    async def declined(self, ctx):
        request = HiscoreRequest.from_embed(ctx.message.embeds[0])
        request_message = await self.__get_original_request_message(ctx, request.channel_id, request.message_id)

        await request_message.reply(f"<@{request.user_id}> Declined :x:")
        await ctx.edit(embeds=RequestEmbed.decline(ctx.message.embeds[0]), components=None)

    @interactions.extension_command()
    async def disable_hiscores_roles(self, ctx):
        """Disabled discord roles for pvm-records.com/hiscores."""
        if user := self.user_settings.get_user_by_id(int(ctx.author.id)):
            self.user_settings.delete(user.user_id)
            await self.role_updater.clear_roles(ctx.author)
            await ctx.send(f"Disabled hiscores roles for {user.hiscores_name}.")
        else:
            await ctx.send(f"Hiscores roles already disabled.", ephemeral=True)

    @interactions.extension_command()
    async def update_roles_manually(self, ctx):
        """Refresh roles manually (only for admins)"""
        if BOT_SETTINGS.admin_role not in ctx.author.roles:
            return await ctx.send(f"Only those with <@&{BOT_SETTINGS.admin_role}> are allowed to update roles.",
                                  ephemeral=True)

        if not await self.hiscores.refresh():
            return await ctx.send("Failed to load hiscores, try again later.", ephemeral=True)

        await ctx.defer()   # allow for up to 15 minutes to execute command instead of 3 seconds

        await self.__update_all_hiscore_roles()

        await ctx.send(f"Roles updated :arrows_counterclockwise:")

    async def __update_all_hiscore_roles(self):
        """Update the roles for all users in user_settings."""
        for user in self.user_settings.get_users():
            member = await self.__get_member_by_id(user.user_id)
            if member:
                await self.role_updater.update_roles(member, self.hiscores.get_entry_by_name(user.hiscores_name))

    async def __enable_hiscore_roles(self, user_id, name):
        """Enable hiscores roles for a new user, generally called after approving a role request.

        :param ctx: component context
        :param int user_id: user ID
        :param str name: hiscores name
        """
        request_author = await self.__get_member_by_id(user_id)
        self.user_settings.update(User(user_id, name))
        await self.role_updater.update_roles(request_author, self.hiscores.get_entry_by_name(name))

    async def __get_original_request_message(self, ctx, channel_id, message_id):
        """Get the original request message, generally used to edit the original message.

        :param interactions.ComponentContext ctx:
        :param int channel_id: ID of the channel where the request was send
        :param int message_id: ID of the request message
        :return: original request message
        :rtype: interactions.Message
        """
        channel = interactions.Channel(**await ctx.client.get_channel(channel_id), _client=ctx.client)
        return await channel.get_message(message_id)

    async def __get_member_by_id(self, member_id):
        """Get a member from the user ID.

        :param int member_id: member ID
        :return: a member or None when no member was found
        :rtype: interactions.Member
        """
        try:
            member = interactions.Member(**await self.client._http.get_member(BOT_SETTINGS.guild, member_id))
        except Exception as e:
            logger.warning(e)
        else:
            return member


def setup(client):
    HiscoresRolesBot(client)
