import re
from dataclasses import dataclass

import interactions

from utils.user_settings import UserSettings, User
from utils.pvm_records.hiscores import Hiscores
from utils.bot_settings import BOT_SETTINGS
from utils.request_embed import RequestData, RequestEmbed


@dataclass(frozen=True)
class HiscoreRequest:
    USER_ID_FIELD = "User ID"
    HISCORES_NAME_FIELD = "Hiscore name"

    channel_id: int
    message_id: int
    user_id: int
    hiscores_name: str

    @classmethod
    def from_embed(cls, embed):
        request = RequestData.from_embed(embed)
        result = re.match(r"<@(\d{18})>", request.fields[HiscoreRequest.USER_ID_FIELD])
        return cls(channel_id=request.channel_id, message_id=request.message_id,
                   user_id=int(result.group(1)),
                   hiscores_name=request.fields[HiscoreRequest.HISCORES_NAME_FIELD])


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
        self.user_settings = UserSettings()
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
        if await self.user_settings.get_user_by_name(name):
            return await ctx.send(f"Hiscore roles already enabled for {name}.")

        await ctx.send(f"Awaiting approval to enable hiscore roles for {name}.")

        admin_channel = interactions.Channel(**await ctx.client.get_channel(BOT_SETTINGS.admin_channel),
                                             _client=ctx.client)

        approval_row = interactions.ActionRow(components=[
            interactions.Button(style=interactions.ButtonStyle.SUCCESS, label="Approve", custom_id="approve"),
            interactions.Button(style=interactions.ButtonStyle.DANGER, label="Decline", custom_id="decline")]
        )

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
        request_embed = RequestEmbed.get_embed(ctx, title="Hiscore roles request", color=0x0099ff, fields=fields)

        await admin_channel.send(embeds=request_embed, components=approval_row)

    @interactions.extension_component("approve")
    async def approved(self, ctx):
        if not self.role_updater.refresh_hiscores():
            return await ctx.send("Failed to load hiscores, try again later.", ephemeral=True)

        request = HiscoreRequest.from_embed(ctx.message.embeds[0])

        await self.__enable_hiscore_roles(ctx, request.user_id, request.hiscores_name)

        request_message = await self.__get_original_request_message(ctx, request.channel_id, request.message_id)
        await request_message.reply(f"<@{request.user_id}>, request approved.")

        await ctx.edit(f"<@{request.user_id}> request to enable hiscore roles for {request.hiscores_name} approved.",
                       embeds=None, components=None)

    @interactions.extension_component("decline")
    async def declined(self, ctx):
        request = HiscoreRequest.from_embed(ctx.message.embeds[0])

        request_message = await self.__get_original_request_message(ctx, request.channel_id, request.message_id)
        await request_message.reply(f"<@{request.user_id}>, request declined.")

        await ctx.edit(f"<@{request.user_id}> request to enable hiscore roles for {request.hiscores_name} declined.",
                       embeds=None, components=None)

    @interactions.extension_command(
        name="disable-hiscores-roles",
        description="Disabled discord roles for pvm-records.com/hiscores.",
        scope=BOT_SETTINGS.guild
    )
    async def disable_hiscores_roles(self, ctx):
        if user := await self.user_settings.get_user_by_id(int(ctx.author.id)):
            await self.role_updater.remove_roles(ctx.author)
            await self.user_settings.delete(user.user_id)
            await ctx.send(f"Disabled hiscores roles for {user.hiscores_name}.")
        else:
            await ctx.send(f"Hiscores roles already disabled.")

    @interactions.extension_command(
        name="update-roles",
        description="Refresh roles manually (only for admins)",
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
        for user in await self.user_settings.get_users():
            member = await self.__get_member_by_id(guild, user.user_id)
            if member:
                await self.role_updater.update_user(member, user.hiscores_name)

    async def __enable_hiscore_roles(self, ctx, user_id, name):
        """Enable hiscores roles for a new user, generally called after approving a role request.

        :param ctx: component context
        :param int user_id: user ID
        :param str name: hiscores name
        """
        guild = await ctx.get_guild()
        request_author = await self.__get_member_by_id(guild, user_id)
        await self.user_settings.update(User(user_id, name))
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
