import sqlite3


class SQLiteConnection:
    """ Singleton чтобы избежать опасности параллельного update в базу. """
    __instance = None

    def __new__(cls, *args, **kwargs):
        """ Возвращает адрес нового созданного объекта """
        if not cls.__instance:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def __init__(self, db_name):
        self.connect = sqlite3.connect(db_name)
        self.cursor = self.connect.cursor()

    def __del__(self):
        self.connect.commit()
        self.connect.close()


DB_NAME = 'users.db'


def insert_to_users(chat_id: int, state: str) -> None:
    try:
        connect = SQLiteConnection(db_name=DB_NAME).connect
        with connect:
            connect.execute("INSERT INTO users (chat_id, state) VALUES (:1, :2) "
                            "ON CONFLICT (chat_id) DO UPDATE SET state=:2", (chat_id, state,))
    except sqlite3.IntegrityError as e:
        print(f'chat_id value "{chat_id}" exists: {repr(e)}')
    except Exception as e:
        print(f"{repr(e)}")


def select_from_users(chat_id: int) -> str | None:
    try:
        connect = SQLiteConnection(db_name=DB_NAME).connect
        with connect:
            c = connect.execute("SELECT state FROM users WHERE chat_id=?", (chat_id,))
            row = c.fetchone()
            return row
    except Exception as e:
        print(f'SELECT value with chat_id "{chat_id}" exit with error: {repr(e)}')


def delete_from_users(chat_id: int) -> None:
    try:
        connect = SQLiteConnection(db_name=DB_NAME).connect
        with connect:
            connect.execute("DELETE FROM users WHERE chat_id=?", (chat_id,))
    except Exception as e:
        print(f'SELECT value with chat_id "{chat_id}" exit with error: {repr(e)}')
