#!/usr/bin/python3

import psycopg2
import os
import pytz
from datetime import datetime
from app.env import Env


class StickerStore:
    def __init__(self):
        self._db_url: str = Env.get_environment('DATABASE_URL', required=True)
        self._ssl_mode: str = Env.get_environment('DATABASE_SSLMODE', default='require', required=False)
        timezone = os.environ.get('TZ')
        if timezone is None:
            self._tz = pytz.timezone(pytz.utc.zone)
        else:
            try:
                self._tz = pytz.timezone(timezone)
            except pytz.UnknownTimeZoneError:
                self._tz = pytz.timezone(pytz.utc.zone)

    def _get_connection(self):
        try:
            connection = psycopg2.connect(self._db_url, sslmode=self._ssl_mode)
        except:
            import traceback
            traceback.print_exc()
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


if __name__ == '__main__':
    db = StickerStore()
    entry = db.fetch_line_sticker_info(line_sticker_id=1425254)
    print(entry)

    entry = db.fetch_line_sticker_info(line_sticker_id=99999999)
    print(entry)
