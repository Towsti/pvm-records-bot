import os
from dataclasses import dataclass
import asyncio

from dotenv import load_dotenv
import psycopg
import time


load_dotenv()


class SingletonMeta(type):
    """
    Singleton implementation from https://refactoring.guru/design-patterns/singleton/python/example#example-0.
    Ensures the same user settings are used for all cogs.
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


@dataclass
class User:
    user_id: int
    hiscores_name: str = None


class UserSettings(metaclass=SingletonMeta):
    DATABASE_URL = os.getenv('DATABASE_URL')

    def __init__(self):
        self.__lock = asyncio.Lock()
        self.__conn = psycopg.connect(UserSettings.DATABASE_URL)

    async def delete(self, user_id):
        async with self.__lock:
            with self.__conn.cursor() as cur:
                cur.execute("""
                DELETE FROM users
                WHERE user_id = %s
                """, (user_id,))
                self.__conn.commit()

    async def update(self, user):
        async with self.__lock:
            with self.__conn.cursor() as cur:
                cur.execute("""
                INSERT INTO users (user_id, hiscores_name) 
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE 
                  SET user_id = excluded.user_id, 
                      hiscores_name = excluded.hiscores_name;
                """, (user.user_id, user.hiscores_name))
                self.__conn.commit()

    async def get_users(self):
        async with self.__lock:
            with self.__conn.cursor() as cur:
                cur.execute("SELECT * FROM users")
                return [User(*record) for record in cur]

    async def get_user_by_id(self, user_id):
        async with self.__lock:
            with self.__conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
                records = list(cur)
                return User(*records[0]) if len(records) > 0 else None

    async def get_user_by_name(self, name):
        async with self.__lock:
            with self.__conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE hiscores_name = %s", (name,))
                records = list(cur)
                return User(*records[0]) if len(records) > 0 else None

    def __del__(self):
        self.__conn.close()
