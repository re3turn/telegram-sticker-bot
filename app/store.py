#!/usr/bin/python3

import logging
import psycopg
from datetime import datetime
from app.env import Env
from app.tz import Tz


class StickerStore:
    def __init__(self):
        self._db_url: str = Env.get_environment('DATABASE_URL', required=True)
        self._ssl_mode: str = Env.get_environment('DATABASE_SSLMODE', default='require', required=False)
        self._tz = Tz.timezone()

    def _get_connection(self):
        try:
            connection = psycopg.connect(self._db_url, sslmode=self._ssl_mode)
        except Exception as e:
            logger.exception(f'Connection error. exception={e.args}')
            return None

        connection.autocommit = True
        return connection

    def fetch_line_sticker_info(self, line_sticker_id):
        with self._get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    'SELECT line_sticker_id, sticker_name, sticker_title '
                    'FROM sticker_info '
                    'WHERE line_sticker_id = %s',
                    (line_sticker_id, ))
                sticker_info = cursor.fetchone()

        return sticker_info

    def insert_sticker_info(self, username, user_id, sticker_title, sticker_name, sticker_id=-1):
        date = datetime.now(self._tz).strftime("%Y/%m/%d %H:%M:%S")
        with self._get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    'INSERT INTO sticker_info (username, user_id, sticker_title, sticker_name, line_sticker_id, date) '
                    'VALUES (%s, %s, %s, %s, %s, %s)',
                    (username, user_id, sticker_title, sticker_name, sticker_id, date))


logger: logging.Logger = logging.getLogger(__name__)


if __name__ == '__main__':
    db = StickerStore()
    entry = db.fetch_line_sticker_info(line_sticker_id=1425254)
    print(entry)

    entry = db.fetch_line_sticker_info(line_sticker_id=99999999)
    print(entry)
