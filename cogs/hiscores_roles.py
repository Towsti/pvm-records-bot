import re

import interactions

from utils.user_settings import UserSettingsControl
from utils.pvm_records.hiscores import Hiscores
from utils.bot_settings import BOT_SETTINGS


class RoleUpdater:
    ROLES = BOT_SETTINGS.hiscores.roles

    def __init__(self):
        self.__hiscores = Hiscores()

    def refresh_hiscores(self):
        return self.__hiscores.refresh()

    async def update_user(self, member, name):
        # todo: check change settings option to update all roles at once
        entry = self.__hiscores.get_entry_by_name(name)

        await self.__update_role(member, RoleUpdater.ROLES.hiscores_leader, entry.is_hiscores_leader())
        await self.__update_role(member, RoleUpdater.ROLES.first_place_holder, entry.first_best())
        await self.__update_role(member, RoleUpdater.ROLES.second_place_holder, entry.second_best())
        await self.__update_role(member, RoleUpdater.ROLES.third_place_holder, entry.third_best())

        max_threshold = False
        for threshold, role_id in RoleUpdater.ROLES.scores:
            if not max_threshold and entry.score >= threshold:
                max_threshold = True
                await self.__update_role(member, role_id, True)
            else:
                await self.__update_role(member, role_id, False)

    async def remove_roles(self, member):
        await self.__update_role(member, RoleUpdater.ROLES.hiscores_leader, False)
        await self.__update_role(member, RoleUpdater.ROLES.first_place_holder, False)
        await self.__update_role(member, RoleUpdater.ROLES.second_place_holder, False)
        await self.__update_role(member, RoleUpdater.ROLES.third_place_holder, False)

        for _, role_id in RoleUpdater.ROLES.scores:
            await self.__update_role(member, role_id, False)

    async def __update_role(self, member, role_id, eligible):
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
        description="Enable discord roles based on pvm-records.com/hiscores",
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
            await ctx.send(f"Hiscore roles already enabled for \"{name}\".")
        else:
            approval_row = interactions.ActionRow(components=[
                interactions.Button(style=interactions.ButtonStyle.SUCCESS, label="Approve", custom_id="approve"),
                interactions.Button(style=interactions.ButtonStyle.DANGER, label="Decline", custom_id="decline"),
                interactions.Button(style=interactions.ButtonStyle.SECONDARY, label="Cancel", custom_id="cancel")])

            await ctx.send(f"Awaiting approval to enable hiscore roles for \"{name}\".", components=approval_row)

    @interactions.extension_component("approve")
    async def approved(self, ctx):
        if BOT_SETTINGS.hiscores.approval_role not in ctx.author.roles:
            await ctx.send("Only admins are allowed to approve or decline highscore roles.", ephemeral=True)
            return

        if not self.role_updater.refresh_hiscores():
            await ctx.send("Failed to load hiscores, try again later.", ephemeral=True)
            return

        user_id = self.__get_original_request_id(ctx)
        name = self.__get_original_request_name(ctx)

        guild = await self.__get_guild_from_context(ctx)
        original_author = await self.__get_member_by_id(guild, user_id)
        self.user_settings.update(str(user_id), name)
        await self.role_updater.update_user(original_author, name)

        await ctx.edit(f"request to enable hiscore roles for \"{name}\" approved.", components=None)

    @interactions.extension_component("decline")
    async def declined(self, ctx):
        if BOT_SETTINGS.hiscores.approval_role not in ctx.author.roles:
            await ctx.send("Only admins are allowed to approve or decline highscore roles.", ephemeral=True)
            return

        name = self.__get_original_request_name(ctx)
        await ctx.edit(f"Request to enable hiscore roles for \"{name}\" declined", components=None)

    @interactions.extension_component("cancel")
    async def cancelled(self, ctx):
        if int(ctx.author.id) != self.__get_original_request_id(ctx):
            return

        await ctx.edit("Cancelled", components=None)

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
            await ctx.send(f"Disabled hiscores roles for \"{name}\"")
        else:
            await ctx.send(f"Hiscores roles already disabled")

    @interactions.extension_command(
        type=interactions.ApplicationCommandType.USER,
        name="Update roles",
        scope=BOT_SETTINGS.guild
    )
    async def update_roles_manually(self, ctx):
        if BOT_SETTINGS.hiscores.approval_role not in ctx.author.roles:
            await ctx.send("Only admins are allowed to update roles.", ephemeral=True)
            return

        if not self.role_updater.refresh_hiscores():
            await ctx.send("Failed to load hiscores, try again later.", ephemeral=True)
            return

        await ctx.defer()   # prevent failing the command when there is no response within 3 seconds

        # update the roles of all users in user_settings.json
        guild = await self.__get_guild_from_context(ctx)
        for user_id, name in self.user_settings.settings.items():
            member = await self.__get_member_by_id(guild, user_id)
            if member:
                await self.role_updater.update_user(member, name)

        # await self.role_updater.update_users(self.user_settings.settings)
        await ctx.send(f"Updated roles.")

    def __get_original_request_id(self, ctx):
        return int(ctx.message._json['interaction']['user']['id'])

    def __get_original_request_name(self, ctx):
        content = ctx.message.content
        result = re.search(r"\"(.*?)\"", content)   # "text "User" text" -> "User"
        return result.group(1)

    async def __get_guild_from_context(self, ctx):
        return await ctx.get_guild()

    async def __get_member_by_id(self, guild, user_id):
        try:
            member = await guild.get_member(user_id)
        except Exception as e:
            print(e)
        else:
            return member


def setup(client):
    HiscoresRolesBot(client)
