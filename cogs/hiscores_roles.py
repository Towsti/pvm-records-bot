import re
from dataclasses import dataclass

import interactions
from dataclasses_json import DataClassJsonMixin

from utils.user_settings import UserSettingsControl
from utils.pvm_records.hiscores import Hiscores
from utils.bot_settings import BOT_SETTINGS


@dataclass(frozen=True)
class RequestMessageProperties(DataClassJsonMixin):
    user_id: int
    message_id: int
    channel_id: int
    hiscores_name: str

    @classmethod
    def from_message_content(cls, content):
        result = re.search(r"```json\n(.*?)\n```", content)

        return cls.from_json(result.group(1))

    def to_message_content(self):
        return f"```json\n{self.to_json()}\n```"


class RoleUpdater:
    def __init__(self):
        self.__hiscores = Hiscores()

    def refresh_hiscores(self):
        """Refresh the hiscores entries with the latest version of pvm-records/hiscores.
        The entries are only updated on a successful refresh.

        :return: refresh successful (True), refresh failed (False)
        :rtype: bool
        """
        return self.__hiscores.refresh()

    async def update_user(self, member, name):
        """Update hiscore roles for a user.

        :param interactions.Member member: discord user to update roles for
        :param name: hiscores name for the user
        """

        # todo: check change settings option to update all roles at once
        entry = self.__hiscores.get_entry_by_name(name)

        await self.__update_role(member, BOT_SETTINGS.hiscore_roles.hiscores_leader, entry.is_hiscores_leader())
        await self.__update_role(member, BOT_SETTINGS.hiscore_roles.first_place_holder, entry.first_best())
        await self.__update_role(member, BOT_SETTINGS.hiscore_roles.second_place_holder, entry.second_best())
        await self.__update_role(member, BOT_SETTINGS.hiscore_roles.third_place_holder, entry.third_best())

        max_threshold = False
        for threshold, role_id in BOT_SETTINGS.hiscore_roles.scores:
            if not max_threshold and entry.score >= threshold:
                max_threshold = True
                await self.__update_role(member, role_id, True)
            else:
                await self.__update_role(member, role_id, False)

    async def remove_roles(self, member):
        """Remove all hiscores roles for a user.

        :param interactions.Member member: discord user to remove roles for
        """
        await self.__update_role(member, BOT_SETTINGS.hiscore_roles.hiscores_leader, False)
        await self.__update_role(member, BOT_SETTINGS.hiscore_roles.first_place_holder, False)
        await self.__update_role(member, BOT_SETTINGS.hiscore_roles.second_place_holder, False)
        await self.__update_role(member, BOT_SETTINGS.hiscore_roles.third_place_holder, False)

        for _, role_id in BOT_SETTINGS.hiscore_roles.scores:
            await self.__update_role(member, role_id, False)

    async def __update_role(self, member, role_id, eligible):
        """Add/remove/keep role for a user based on eligibility

        :param interactions.Member member: discord user to remove roles for
        :param int role_id: hiscore role ID to update
        :param bool eligible: user eligible for role (True), user not eligible (False)
        """
        if eligible:
            if role_id not in member.roles:
                await member.add_role(role_id, BOT_SETTINGS.guild)
        else:
            if role_id in member.roles:
                await member.remove_role(role_id, BOT_SETTINGS.guild)


class HiscoresRolesBot(interactions.Extension):
    def __init__(self, client):
        self.client = client
        self.user_settings = UserSettingsControl()
        self.role_updater = RoleUpdater()

    @interactions.extension_command(
        name="enable-hiscores-roles",
        description="Enable discord roles based on pvm-records.com/hiscores.",
        scope=BOT_SETTINGS.guild,
        options=[
            interactions.Option(
                name="name",
                description="pvm-records.com/hiscores name",
                type=interactions.OptionType.STRING,
                required=True,
            )
        ]
    )
    async def enable_hiscores_roles(self, ctx, name):
        if name in self.user_settings.settings.values():
            return await ctx.send(f"Hiscore roles already enabled for {name}.")

        await ctx.send(f"Awaiting approval to enable hiscore roles for {name}.")

        properties = RequestMessageProperties(user_id=int(ctx.author.id), message_id=int(ctx.message.id),
                                              channel_id=int(ctx.channel_id), hiscores_name=name)

        admin_channel = interactions.Channel(**await ctx.client.get_channel(BOT_SETTINGS.admin_channel),
                                             _client=ctx.client)

        approval_row = interactions.ActionRow(components=[
            interactions.Button(style=interactions.ButtonStyle.SUCCESS, label="Approve", custom_id="approve"),
            interactions.Button(style=interactions.ButtonStyle.DANGER, label="Decline", custom_id="decline")])

        await admin_channel.send(properties.to_message_content() +
                                 f"{ctx.author.mention} requesting to enable hiscore roles for {name}.",
                                 components=approval_row)

    @interactions.extension_component("approve")
    async def approved(self, ctx):
        if not self.role_updater.refresh_hiscores():
            return await ctx.send("Failed to load hiscores, try again later.", ephemeral=True)

        request = RequestMessageProperties.from_message_content(ctx.message.content)

        await self.__enable_hiscore_roles(ctx, request.user_id, request.hiscores_name)

        message = await self.__get_original_request_message(ctx, request.channel_id, request.message_id)

        # update the original request and admin approval message
        approve_message = f"request to enable hiscore roles for {request.hiscores_name} approved"
        await message.edit(approve_message)
        await ctx.edit(approve_message, components=None)

    @interactions.extension_component("decline")
    async def declined(self, ctx):
        request = RequestMessageProperties.from_message_content(ctx.message.content)

        message = await self.__get_original_request_message(ctx, request.channel_id, request.message_id)

        # update the original request and admin decline message
        decline_message = f"request to enable hiscore roles for {request.hiscores_name} declined"
        await message.edit(decline_message)
        await ctx.edit(decline_message, components=None)

    @interactions.extension_command(
        name="disable-hiscores-roles",
        description="Disabled discord roles for pvm-records.com/hiscores.",
        scope=BOT_SETTINGS.guild
    )
    async def disable_hiscores_roles(self, ctx):
        user_id = str(ctx.author.id)

        if user_id in self.user_settings.settings:
            await self.role_updater.remove_roles(ctx.author)
            name = self.user_settings.remove(user_id)
            await ctx.send(f"Disabled hiscores roles for {name}.")
        else:
            await ctx.send(f"Hiscores roles already disabled.")

    @interactions.extension_command(
        type=interactions.ApplicationCommandType.USER,
        name="Update roles",
        scope=BOT_SETTINGS.guild
    )
    async def update_roles_manually(self, ctx):
        if BOT_SETTINGS.admin_role not in ctx.author.roles:
            return await ctx.send("Only admins are allowed to update roles.", ephemeral=True)

        if not self.role_updater.refresh_hiscores():
            return await ctx.send("Failed to load hiscores, try again later.", ephemeral=True)

        await ctx.defer()   # allow for up to 15 minutes to execute command instead of 3 seconds

        await self.__update_all_hiscore_roles(ctx)

        await ctx.send(f"Updated roles.")

    async def __update_all_hiscore_roles(self, ctx):
        """Update the roles for all users in user_settings.

        :param Union[interactions.CommandContext, interactions.ComponentContext] ctx: command/component context
        """
        guild = await ctx.get_guild()
        for user_id, name in self.user_settings.settings.items():
            member = await self.__get_member_by_id(guild, int(user_id))
            if member:
                await self.role_updater.update_user(member, name)

    async def __enable_hiscore_roles(self, ctx, user_id, name):
        """Enable hiscores roles for a new user, generally called after approving a role request.

        :param ctx: component context
        :param int user_id: user ID
        :param str name: hiscores name
        """
        guild = await ctx.get_guild()
        request_author = await self.__get_member_by_id(guild, user_id)
        self.user_settings.update(str(user_id), name)
        await self.role_updater.update_user(request_author, name)

    async def __get_original_request_message(self, ctx, channel_id, message_id):
        """Get the original request message, generally used to edit the original message.

        :param interactions.ComponentContext ctx:
        :param int channel_id: ID of the channel where the request was send
        :param int message_id: ID of the request message
        :return: original request message
        :rtype: interactions.Message
        """
        channel = interactions.Channel(**await ctx.client.get_channel(channel_id),
                                       _client=ctx.client)
        return await channel.get_message(message_id)

    async def __get_member_by_id(self, guild, user_id):
        """Get a guild member from the user ID.

        :param interactions.Guild guild: guild to look for user
        :param int user_id: user ID
        :return: a member or None when no member was found
        :rtype: interactions.Member
        """
        try:
            member = await guild.get_member(user_id)
        except Exception as e:
            print(e)
        else:
            return member


def setup(client):
    HiscoresRolesBot(client)
