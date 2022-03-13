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
        self.__pool = ConnectionPool(Database.DATABASE_URL, min_size=0, max_size=5)
        atexit.register(self.__pool.close)

    @contextmanager
    def query(self):
        with self.__pool.connection() as conn:
            with conn.cursor() as cur:
                yield conn, cur


class DatabaseClient(metaclass=SingletonMeta):
    """Should be inherited by clients.
    Every client should interact with a table (e.g. UserSettings).
    Singleton for DatabaseClient + Database ensures that there is only 1 Database() instance.
    There can be multiple clients but only 1 instance of each client.

    Example
    -------
    # utils/database/user_settings.py
    class UserSettings(DatabaseClient)

    # utils/database/seasonals.py
    class SeasonalSettings(DatabaseClient)

    # cogs/hiscore_roles.py
    user_settings = UserSettings()

    # cogs/seasonals.py
    user_settings = UserSettings()
    seasonal_settings = SeasonalSettings()

    # validation
    assert hiscore_roles.user_settings == seasonals.user_settings
    assert hiscore_roles.user_settings != seasonals.seasonal_settings
    assert seasonals.user_settings != seasonals.seasonal_settings
    assert hiscore_roles.user_settings._database == seasonals.user_settings._database == seasonals.seasonal_settings
    """
    def __init__(self):
        self._database = Database()
