from dataclasses import dataclass

from utils.database.database import DatabaseClient


@dataclass
class User:
    user_id: int
    hiscores_name: str = None


class UserSettings(DatabaseClient):
    def delete(self, user_id):
        with self._database.query() as conn:
            conn.execute("""
            DELETE FROM users
            WHERE user_id = %s
            """, (user_id,))

    def update(self, user):
        with self._database.query() as conn:
            conn.execute("""
            INSERT INTO users (user_id, hiscores_name) 
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE 
              SET user_id = excluded.user_id, 
                  hiscores_name = excluded.hiscores_name;
            """, (user.user_id, user.hiscores_name))

    def get_users(self):
        with self._database.query(User) as conn:
            return conn.execute("SELECT * FROM users").fetchall()

    def get_user_by_id(self, user_id):
        with self._database.query(User) as conn:
            return conn.execute("SELECT * FROM users WHERE user_id = %s", (user_id,)).fetchone()

    def get_user_by_hiscores_name(self, hiscores_name):
        with self._database.query(User) as conn:
            return conn.execute("SELECT * FROM users WHERE hiscores_name = %s", (hiscores_name,)).fetchone()

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
