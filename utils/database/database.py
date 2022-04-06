import os
from contextlib import contextmanager
import atexit

from dotenv import load_dotenv
from psycopg_pool import ConnectionPool
from psycopg.rows import class_row


load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')


class SingletonMeta(type):
    """Singleton to ensure a single db connection across all clients."""

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class Database(metaclass=SingletonMeta):
    """Main database connection, only 1 instance allowed."""

    def __init__(self):
        self.__pool = ConnectionPool(DATABASE_URL, min_size=0, max_size=5)
        atexit.register(self.__pool.close)

    @contextmanager
    def query(self, class_=None):
        """Perform a query and return the connection object.

        :param class_: optional row factory to return rows as a dataclass (e.g. class_=User)
        :return: pool connection
        """
        with self.__pool.connection() as conn:
            if class_:
                conn.row_factory = class_row(class_)
            yield conn


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
