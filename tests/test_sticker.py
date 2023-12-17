import asyncio
import asynctest
import glob
import shutil
import os
import subprocess
import nose2.tools
from PIL import Image
from telebot.types import Message
from telebot.async_telebot import AsyncTeleBot
from unittest.mock import MagicMock
from app.sticker import Sticker
from app.store import StickerStore

TEST_CHAT_ID = 999999
TEST_USER_ID = 999999
TEST_USER_NAME = "test"
TEST_MESSAGE = Message.de_json({
    "content_type": "text",
    "id": 774,
    "message_id": 774,
    "from_user": {
        "id": 1111111,
        "username": "test",
        "first_name": "test",
        "last_name": None
    },
    "chat": {
        "id": 1111111,
        "type": "private",
        "title": None,
        "username": "test",
        "first_name": "test",
        "last_name": None,
        "photo": None,
        "bio": None,
        "has_private_forwards": None,
        "description": None,
        "invite_link": None,
        "pinned_message": None,
        "permissions": None,
        "slow_mode_delay": None,
        "message_auto_delete_time": None,
        "has_protected_content": None,
        "sticker_set_name": None,
        "can_set_sticker_set": None,
        "linked_chat_id": None,
        "location": None
    },
    "date": 1652005425,
    "text": "test",
    "json": {
        "message_id": 774,
        "from": {
            "id": 1111111,
            "is_bot": False,
            "first_name": "test",
            "username": "test",
            "language_code": "ja"
        },
        "chat": {
            "id": 1111111,
            "first_name": "test",
            "username": "test",
            "type": "private"
        },
        "date": 1652005425,
        "text": "test"
    }
})
TEST_DATABASE_URL = 'postgres://username:password@hostname:port/database'


class TestSticker:
    def __init__(self):
        self._mock_bot = None
        os.environ['DATABASE_URL'] = TEST_DATABASE_URL

    def setUp(self):
        self._mock_bot = asynctest.patch('telebot.async_telebot.AsyncTeleBot',
                                         autospec=AsyncTeleBot)

    def tearDown(self):
        sticker_dir = './stickers'
        if os.path.isdir(sticker_dir):
            sub = subprocess.Popen(f'rm -r {sticker_dir}', shell=True)
            subprocess.Popen.wait(sub)

    @nose2.tools.params(
        (123, 123),
        (512, 512),
        (2000, 1000))
    def test_new_size(self, width, height):
        new_w, new_h = Sticker.new_size(width, height)
        actual = max(new_w, new_h)
        assert actual == 512

    def test_resize_sticker(self):
        sticker = Sticker(self._mock_bot, TEST_USER_NAME, TEST_USER_ID, TEST_MESSAGE)
        for filename in glob.glob('./tests/static/png/*.*'):
            shutil.copy(filename, sticker._sticker_dir)
        sticker.resize_sticker()
        png_list = glob.glob(f'{sticker._sticker_dir}/*.png')
        for png in png_list:
            img = Image.open(png)
            width, height = img.size
            actual = max(width, height)
            assert actual == 512

    def test_download_line_sticker(self):
        sticker = Sticker(self._mock_bot, TEST_USER_NAME, TEST_USER_ID, TEST_MESSAGE, 1646410)
        sticker.download_line_sticker()
        _, _, files = next(os.walk(sticker._sticker_dir))
        actual = len(files)
        assert actual == 16

    @nose2.tools.params(
        ("1215735", False, 'en', 'Winter emblem'),
        ("1215735", False, 'ja', '冬のワッペン'),
        ("8988", False, 'ko', '아리스토캣: 크레용 버전'),
        ("1130155", False, 'ja', 'ヨグまつ'),  # selling discontinued sticker
        ('62bbba25bc523362ed0bdf11', True, 'en', 'PAC-MAN Emoji'),
        ("9999999999999", False, 'en', ''),
    )
    def test_fetch_line_sticker_title(self, sticker_id: str, is_emoji, region, ans):
        sticker = Sticker(self._mock_bot, TEST_USER_NAME, TEST_USER_ID, TEST_MESSAGE, sticker_id)
        actual = sticker.fetch_line_sticker_title(is_emoji=is_emoji, region=region)
        assert actual == ans

    @nose2.tools.params(
        ("-1", False, "abcdef", 'abcdef_by_testbot'),
        ("9365573", False, None, 'Hitori_9365573_by_testbot'),
        ("1215735", False, None, 'Winter_1215735_by_testbot'),
        ("14056952", False, None, 'DK_14056952_by_testbot'),
        ("62bbba25bc523362ed0bdf11", True, None, 'PAC-MAN_62bbba_by_testbot'),
        ("9999999999999", False, None, 'line_9999999999999_by_testbot'),
    )
    def test_generate_sticker_name(self, sticker_id: str, is_emoji, file_name, ans):
        self._mock_bot.getMe = asynctest.Mock(side_effect=MockTelepot.mock_get_me)
        sticker = Sticker(self._mock_bot, TEST_USER_NAME, TEST_USER_ID, TEST_MESSAGE, sticker_id)
        loop = asyncio.get_event_loop()
        actual = loop.run_until_complete(sticker.generate_sticker_name(is_emoji=is_emoji, file_name=file_name))
        assert actual == ans

    def test_unzip_sticker(self):
        sticker = Sticker(self._mock_bot, TEST_USER_NAME, TEST_USER_ID, TEST_MESSAGE)
        shutil.copy('./tests/static/zip/test.zip', sticker._sticker_dir)
        sticker.unzip_sticker('test.zip')
        _, dirs, files = next(os.walk(sticker._sticker_dir))
        assert len(files) == 3
        assert len(dirs) == 1

    @nose2.tools.params(
        ('exists_sticker_set_by_testbot', True),
        ('new_sticker_set_by_testbot', False)
    )
    def test_is_already_sticker_name(self, sticker_set_name, ans):
        sticker = Sticker(self._mock_bot, TEST_USER_NAME, TEST_USER_ID, TEST_MESSAGE)
        self._mock_bot.getStickerSet = asynctest.Mock(side_effect=MockTelepot.mock_get_sticker_set)
        loop = asyncio.get_event_loop()
        actual = loop.run_until_complete(sticker.is_already_sticker_name(sticker_set_name))
        assert actual is ans

    @nose2.tools.params(
        ('new sticker', 'new_sticker_set_by_testbot', True),
        ('exists_sticker', 'exists_sticker_set_by_testbot', False),
        ('add_error_sticker', 'add_error_sticker_set_by_testbot', False),
        ('except_sticker', 'except_sticker_set_by_testbot', False)
    )
    def test_create_sticker_set(self, sticker_title, sticker_set_name, ans):
        sticker = Sticker(self._mock_bot, TEST_USER_NAME, TEST_USER_ID, TEST_MESSAGE)
        for filename in glob.glob('./tests/static/png/*.*'):
            shutil.copy(filename, sticker._sticker_dir)
        self._mock_bot.uploadStickerFile = asynctest.Mock(side_effect=MockTelepot.mock_upload_sticker_file)
        self._mock_bot.createNewStickerSet = asynctest.Mock(side_effect=MockTelepot.mock_create_new_sticker_set)
        self._mock_bot.addStickerToSet = asynctest.Mock(side_effect=MockTelepot.mock_add_sticker_to_set)
        sticker.delete_sticker_set = asynctest.Mock(side_effect=self.mock_delete_sticker_set)
        loop = asyncio.get_event_loop()
        actual = loop.run_until_complete(sticker.create_sticker_set(sticker_title, sticker_set_name))
        assert actual is ans

    @nose2.tools.params(
        ('https://google.com', False),
        ('https://store.line.me/stickershop/product/12357', True),  # Already add
        ('https://store.line.me/stickershop/product/12356', True)   # New add
    )
    def test_register_line_sticker(self, command, ans):
        self._mock_bot.sendMessage = asynctest.Mock(side_effect=MockTelepot.mock_send_message)
        self._mock_bot.getMe = asynctest.Mock(side_effect=MockTelepot.mock_get_me)
        sticker = Sticker(self._mock_bot, TEST_USER_NAME, TEST_USER_ID, TEST_MESSAGE)
        sticker.create_sticker_set = asynctest.Mock(side_effect=self.mock_create_sticker_set)
        StickerStore.insert_sticker_info = MagicMock(side_effect=self.mock_insert_sticker_info)
        StickerStore.fetch_line_sticker_info = MagicMock(side_effect=self.mock_fetch_line_sticker_info)
        loop = asyncio.get_event_loop()
        actual = loop.run_until_complete(sticker.register_line_sticker(command))
        assert actual is ans

    def register_zip_sticker(self):
        pass

    @staticmethod
    async def mock_delete_sticker_set(sticker_name):
        pass

    @staticmethod
    async def mock_create_sticker_set(sticker_title, sticker_name):
        return True

    @staticmethod
    def mock_insert_sticker_info(username, user_id, sticker_title, sticker_name, sticker_id):
        return True

    @staticmethod
    def mock_fetch_line_sticker_info(sticker_id):
        if sticker_id != 12357:
            return None

        return sticker_id, 'SNOOPY', 'スヌーピー　PEANUTS SPORTS'


class MockTelepot:
    @staticmethod
    async def mock_get_me():
        return {'username': 'testbot'}

    @staticmethod
    async def mock_get_sticker_set(sticker_set_name):
        if sticker_set_name != 'exists_sticker_set_by_testbot':
            return None
        return {'name': 'exists_sticker_set_by_testbot'}

    @staticmethod
    async def mock_upload_sticker_file(user_id, png):
        return {'file_id': user_id}

    @staticmethod
    async def mock_create_new_sticker_set(user_id, sticker_set_name, sticker_title, file_id, emojis):
        if sticker_set_name == 'exists_sticker_set_by_testbot':
            return False
        if sticker_set_name == 'except_sticker_set_by_testbot':
            raise Exception()
        return True

    @staticmethod
    async def mock_add_sticker_to_set(user_id, sticker_set_name, file_id, emojis):
        if sticker_set_name == 'add_error_sticker_set_by_testbot':
            return False
        return True

    @staticmethod
    async def mock_send_message(chat_id, text):
        pass


if __name__ == '__main__':
    nose2.main()
