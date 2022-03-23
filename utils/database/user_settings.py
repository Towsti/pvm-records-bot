from dataclasses import dataclass

from utils.database.database import DatabaseClient


@dataclass
class User:
    user_id: int
    hiscores_name: str = None


class UserSettings(DatabaseClient):
    def __init__(self):
        super().__init__()

    def delete(self, user_id):
        with self._database.query() as (conn, cur):
            cur.execute("""
            DELETE FROM users
            WHERE user_id = %s
            """, (user_id,))

            conn.commit()

    def update(self, user):
        with self._database.query() as (conn, cur):
            cur.execute("""
            INSERT INTO users (user_id, hiscores_name) 
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE 
              SET user_id = excluded.user_id, 
                  hiscores_name = excluded.hiscores_name;
            """, (user.user_id, user.hiscores_name))

            conn.commit()

    def get_users(self):
        with self._database.query() as (conn, cur):
            cur.execute("SELECT * FROM users")
            return [User(*record) for record in cur]

    def get_user_by_id(self, user_id):
        with self._database.query() as (conn, cur):
            cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            records = list(cur)
            if len(records) > 0:
                return User(*records[0])

    def get_user_by_hiscores_name(self, hiscores_name):
        with self._database.query() as (conn, cur):
            cur.execute("SELECT * FROM users WHERE hiscores_name = %s", (hiscores_name,))
            records = list(cur)
            if len(records) > 0:
                return User(*records[0])

    @staticmethod
    def find_user_by_id(user_id, users):
        for user in users:
            if user_id == user.user_id:
                return user

    @staticmethod
    def find_user_by_hiscores_name(hiscores_name, users):
        for user in users:
            if hiscores_name == user.hiscores_name:
                return user
