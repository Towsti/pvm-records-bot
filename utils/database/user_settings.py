import logging
from dataclasses import dataclass
from abc import ABC, abstractmethod

from .database import DatabaseClient


logger = logging.getLogger(__name__)


@dataclass
class User:
    user_id: int
    display_name: str = None


class UserSettingsObserver(ABC):
    """Implement observer for clients/cogs that need to update on a user settings change."""

    @abstractmethod
    async def user_updated(self, user):
        """Event when a user is added or updated in the user settings database.

        :param User user: updated/added user
        """
        raise NotImplementedError()

    @abstractmethod
    async def user_removed(self, user):
        """Event when a new user is removed from the user settings database.

        :param User user: updated/added user
        """
        raise NotImplementedError()


class UserSettings(DatabaseClient):
    """User settings database client."""

    def __init__(self):
        super().__init__()
        self.__observers = list()

    def subscribe(self, observer):
        """Add new observer.

        :param UserSettingsObserver observer: observer instance
        """
        self.__observers.append(observer)

    async def __notify_updated(self, user):
        """Synchronously notify all observers that a user is updated/added.

        :param UserSettingsObserverUser user: updated user
        """
        for observer in self.__observers:
            await observer.user_updated(user)
            logger.debug(f"notify updated: {observer}")

    async def __notify_removed(self, user):
        """Synchronously notify all observers that a user is deleted.

        :param User user: deleted user
        """
        for observer in self.__observers:
            await observer.user_removed(user)
            logger.debug(f"notify removed: {observer}")

    async def delete(self, user_id):
        """Delete a user from user settings data base.

        :param int user_id: remove user by user ID
        """
        with self._database.query() as conn:
            conn.execute("""
            DELETE FROM users
            WHERE user_id = %s
            """, (user_id,))
        await self.__notify_removed(User(user_id))

    async def update(self, user):
        """Update or add a new user.

        :param User user: user settings
        """
        with self._database.query() as conn:
            conn.execute("""
            INSERT INTO users (user_id, display_name) 
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE 
              SET user_id = excluded.user_id, 
                  display_name = excluded.display_name;
            """, (user.user_id, user.display_name))
        await self.__notify_updated(user)

    def get_users(self):
        """Get all users in the user settings database.

        :return: list of all users
        :rtype: list[User]
        """
        with self._database.query(User) as conn:
            return conn.execute("SELECT * FROM users").fetchall()

    def get_user_by_id(self, user_id):
        """Find specific user by the user ID.

        :param int user_id: user ID
        :return: user or None if no user is found
        :rtype: User
        """
        with self._database.query(User) as conn:
            return conn.execute("SELECT * FROM users WHERE user_id = %s", (user_id,)).fetchone()

    def get_user_by_display_name(self, display_name):
        """Find specific user by the pvm-records.com user display name.

        :param str display_name: pvm-records.com display name
        :return: user or None if no user is found
        :rtype: User
        """
        with self._database.query(User) as conn:
            return conn.execute("SELECT * FROM users WHERE display_name = %s", (display_name,)).fetchone()

    @staticmethod
    def find_user_by_id(user_id, users):
        """Find a user in a list of all users by user ID

        :param int user_id: user ID
        :param list[User] users: list of users
        :return: user or None if no user is found
        :rtype: User
        """
        for user in users:
            if user_id == user.user_id:
                return user

    @staticmethod
    def find_user_by_display_name(display_name, users):
        """Find a user in a list of all users by pvm-records.com display name

        :param display_name: pvm-records.com display name
        :param list[User] users: list of users
        :return: user or None if no user is found
        :rtype: User
        """
        for user in users:
            if display_name == user.display_name:
                return user
