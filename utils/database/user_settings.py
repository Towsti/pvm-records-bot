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
    @abstractmethod
    async def user_updated(self, user):
        raise NotImplementedError()

    @abstractmethod
    async def user_removed(self, user):
        raise NotImplementedError()


class UserSettings(DatabaseClient):
    def __init__(self):
        super().__init__()
        self.__observers = list()

    def subscribe(self, observer):
        self.__observers.append(observer)

    async def __notify_updated(self, user):
        for observer in self.__observers:
            await observer.user_updated(user)
            logger.debug(f"notify updated: {observer}")

    async def __notify_removed(self, user):
        for observer in self.__observers:
            await observer.user_removed(user)
            logger.debug(f"notify removed: {observer}")

    async def delete(self, user_id):
        with self._database.query() as conn:
            conn.execute("""
            DELETE FROM users
            WHERE user_id = %s
            """, (user_id,))
        await self.__notify_removed(User(user_id))

    async def update(self, user):
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
        with self._database.query(User) as conn:
            return conn.execute("SELECT * FROM users").fetchall()

    def get_user_by_id(self, user_id):
        with self._database.query(User) as conn:
            return conn.execute("SELECT * FROM users WHERE user_id = %s", (user_id,)).fetchone()

    def get_user_by_display_name(self, display_name):
        with self._database.query(User) as conn:
            return conn.execute("SELECT * FROM users WHERE display_name = %s", (display_name,)).fetchone()

    @staticmethod
    def find_user_by_id(user_id, users):
        for user in users:
            if user_id == user.user_id:
                return user

    @staticmethod
    def find_user_by_display_name(display_name, users):
        for user in users:
            if display_name == user.display_name:
                return user
