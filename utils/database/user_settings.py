from dataclasses import dataclass

from utils.database.database import Database


@dataclass
class User:
    user_id: int
    hiscores_name: str = None


class UserSettings(Database):
    def __init__(self):
        super().__init__()

    def delete(self, user_id):
        with super()._query() as (conn, cur):
            cur.execute("""
            DELETE FROM users
            WHERE user_id = %s
            """, (user_id,))

            conn.commit()

    def update(self, user):
        with super()._query() as (conn, cur):
            cur.execute("""
            INSERT INTO users (user_id, hiscores_name) 
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE 
              SET user_id = excluded.user_id, 
                  hiscores_name = excluded.hiscores_name;
            """, (user.user_id, user.hiscores_name))

            conn.commit()

    def get_users(self):
        with super()._query() as (conn, cur):
            cur.execute("SELECT * FROM users")
            return [User(*record) for record in cur]

    def get_user_by_id(self, user_id):
        with super()._query() as (conn, cur):
            cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            records = list(cur)
            if len(records) > 0:
                return User(*records[0])

    def get_user_by_hiscores_name(self, hiscores_name):
        with super()._query() as (conn, cur):
            cur.execute("SELECT * FROM users WHERE hiscores_name = %s", (hiscores_name,))
            records = list(cur)
            if len(records) > 0:
                return User(*records[0])
