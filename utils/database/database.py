import os
from contextlib import contextmanager
import atexit

from dotenv import load_dotenv
from psycopg_pool import ConnectionPool


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


class Database(metaclass=SingletonMeta):
    DATABASE_URL = os.getenv('DATABASE_URL')

    def __init__(self):
        self._pool = ConnectionPool(Database.DATABASE_URL, min_size=0, max_size=5)
        atexit.register(self._pool.close)

    @contextmanager
    def _query(self):
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                yield conn, cur
