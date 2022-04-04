import os
import logging

from dotenv import load_dotenv
import interactions

from utils.bot_settings import BOT_SETTINGS
from utils.database.user_settings import UserSettings, UserSettingsObserver
from utils.pvm_records.hiscores import Hiscores, Entry
from utils.embeds.new_record_webhook import NewRecord

logger = logging.getLogger(__name__)

load_dotenv()

WEBHOOK_TOKEN = os.getenv('WEBHOOK_TOKEN')


class RoleUpdater:
    def __init__(self, http_client):
        super().__init__()
        self.__http = http_client
        self.__guild = BOT_SETTINGS.guild
        self.__roles = BOT_SETTINGS.hiscore_roles

    async def clear_roles(self, member):
        for role, eligible in Entry.empty().get_eligible_roles(self.__roles):
            await self.__update_role(member, role, eligible)

    async def update_roles(self, member, hiscores_entry):
        for role, eligible in hiscores_entry.get_eligible_roles(self.__roles):
            await self.__update_role(member, role, eligible)

    async def __update_role(self, member, role, eligible):
        if not member.roles:
            # todo: remove when no longer required
            # member.roles attribute now set to None instead of [] when there are no roles
            member.roles = list()

        try:
            if eligible:
                if role not in member.roles:
                    await self.__http.add_member_role(self.__guild, member.id, role)
            else:
                if role in member.roles:
                    await self.__http.remove_member_role(self.__guild, member.id, role)
        except Exception as e:
            # lazy exception handling in case user leaves when role is being updated
            logger.warning(e)


class HiscoresRolesBot(interactions.Extension, UserSettingsObserver):
    # todo: implement observer as decorator to avoid multiple inheritance
    def __init__(self, client):
        self.client = client
        self.role_updater = RoleUpdater(client._http)
        self.user_settings = UserSettings()
        self.hiscores = Hiscores()

    @interactions.extension_listener()
    async def on_ready(self):
        self.user_settings.subscribe(self)

    @interactions.extension_listener()
    async def on_message_create(self, message):
        if int(message.author.id) == BOT_SETTINGS.new_record.webhook:
            await self.__send_new_record(message)
            if await self.hiscores.refresh():
                await self.__update_all_hiscore_roles()
                await self.client._http.send_message(BOT_SETTINGS.admin_channel,
                                                     "Roles updated :arrows_counterclockwise:")

    @interactions.extension_command()
    async def refresh_hiscores_roles(self, ctx):
        """Refresh hiscores roles manually (admins only)."""
        if ctx.author.roles is None or BOT_SETTINGS.admin_role not in ctx.author.roles:
            return await ctx.send(f"Only those with <@&{BOT_SETTINGS.admin_role}> are allowed to update roles.",
                                  ephemeral=True)

        if not await self.hiscores.refresh():
            return await ctx.send(":warning: Failed to load hiscores, try again later.", ephemeral=True)

        await ctx.defer()  # allow for up to 15 minutes to execute command

        await self.__update_all_hiscore_roles()
        await ctx.send(f"Roles updated :arrows_counterclockwise:")

    @interactions.extension_message_command()
    async def resend_new_record(self, ctx):
        """Resend a new record webhook."""
        if int(ctx.target.author.id) != BOT_SETTINGS.new_record.webhook:
            return await ctx.send("this is not a new record webhook", ephemeral=True)

        await self.__send_new_record(ctx.target)

        if not await self.hiscores.refresh():
            return await ctx.send(":warning: Failed to load hiscores, try again later.", ephemeral=True)

        await ctx.defer()  # allow for up to 15 minutes to execute command

        await self.__update_all_hiscore_roles()
        await ctx.send("Roles updated :arrows_counterclockwise:")

    async def user_updated(self, user):
        """Event, update roles when a user is linked.

        :param User user: newly linked user
        """
        if not await self.hiscores.refresh():
            return

        if member := await self.__get_member_by_id(user.user_id):
            entry = self.hiscores.get_entry_by_name(user.display_name)
            await self.role_updater.update_roles(member, entry)

    async def user_removed(self, user):
        """Event, remove roles when a user is unlinked.

        :param User user: unlinked user
        """
        if member := await self.__get_member_by_id(user.user_id):
            await self.role_updater.clear_roles(member)

    async def __update_all_hiscore_roles(self):
        """Update the roles for all users configured in user settings database.
        Clear roles for all users that aren't configured in user settings.
        """
        configured_users = self.user_settings.get_users()

        members = await self.client._http.get_list_of_members(BOT_SETTINGS.guild, 1000)
        for member_dict in members:
            member = interactions.Member(**member_dict)
            if user_settings := UserSettings.find_user_by_id(int(member.id), configured_users):
                entry = self.hiscores.get_entry_by_name(user_settings.display_name)
                await self.role_updater.update_roles(member, entry)
            else:
                await self.role_updater.clear_roles(member)

    async def __send_new_record(self, message):
        """Send a new record message from a new record embed.

        :param message: new record webhook message
        """
        embed = message.embeds[0]

        new_record = NewRecord.from_webhook(embed)
        new_record.set_player_ids(self.user_settings.get_users())

        await self.client._http.send_message(BOT_SETTINGS.new_record.channel, str(new_record))
        await self.client._http.edit_webhook_message(message.webhook_id, WEBHOOK_TOKEN, message.id,
                                                     {'embeds': [NewRecord.webhook_sent_embed(embed)._json]})

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
