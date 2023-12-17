#!/usr/bin/python3

import logging
import glob
import os
import urllib.request
import urllib.error
import re

import pyquery
import zipfile
import shutil
import subprocess
import traceback
from PIL import Image
from telebot.async_telebot import AsyncTeleBot
from telebot import types

from .env import Env
from .unicode_string import UnicodeString
from .store import StickerStore

MAX_STICKER_SIZE = 512


class Sticker:
    def __init__(self, bot: AsyncTeleBot, username: str, user_id: int, message: types.Message, sticker_id="-1"):
        self._username = username
        self._user_id = user_id
        self._message = message
        self._bot = bot
        self._sticker_id: str = sticker_id
        self._user_dir = f'./stickers/{user_id}'
        self._sticker_dir: str = self._user_dir
        self._is_emoji = False
        os.makedirs(self._user_dir, exist_ok=True)

    def set_sticker_id(self, sticker_id: str):
        self._sticker_id = sticker_id

    def set_is_emoji(self, is_emoji):
        self._is_emoji = is_emoji

    def set_sticker_dir(self, sticker_id="-1", zip_file_name=None):
        if sticker_id == "-1":
            if zip_file_name is None:
                self._sticker_dir = f'{self._user_dir}/zip'
            else:
                self._sticker_dir = f'{self._user_dir}/{zip_file_name}'
        else:
            self._sticker_dir = f'{self._user_dir}/{self._sticker_id}'

    @staticmethod
    def new_size(width, height):
        round = (lambda x: (x * 2 + 1) // 2)
        # Must not exceed 512px, and either width or height must be exactly 512px
        if width + height <= MAX_STICKER_SIZE * 2:
            scale = MAX_STICKER_SIZE / float(max(width, height))
            new_width = int(round(scale * width))
            new_height = int(round(scale * height))
        else:
            scale = max(width, height) / float(MAX_STICKER_SIZE)
            new_width = int(round(width / scale))
            new_height = int(round(height / scale))
        return new_width, new_height

    def resize_sticker(self):
        # Must be up to 512 KB in size
        pngquant = 'pngquant --skip-if-larger --speed 1 --ext .png --force'
        png_list = glob.glob(f'{self._sticker_dir}/*.[jJpP][pPnN][gG]')
        for png in png_list:
            img = Image.open(png)
            png = f'{os.path.splitext(png)[0]}.png'
            original_w, original_h = img.size
            new_w, new_h = self.new_size(original_w, original_h)
            img = img.convert('RGBA').resize((new_w, new_h), Image.LANCZOS)
            img.save(png, 'png')

        png_list = glob.glob(f'{self._sticker_dir}/*.png')
        sub_list = []
        for png in png_list:
            sub_list.append(subprocess.Popen(f'{pngquant} {png}', shell=True))

        for sub in sub_list:
            subprocess.Popen.wait(sub)

    def download_line_sticker(self):
        download_dir = self._sticker_dir
        zip_path = f'{download_dir}/{self._sticker_id}.zip'

        if self._is_emoji:
            zip_url = f'https://stickershop.line-scdn.net/sticonshop/v1/{self._sticker_id}/sticon/iphone/package.zip'
        else:
            zip_url = (f'https://stickershop.line-scdn.net/stickershop/v1/product/'
                       f'{self._sticker_id}/iphone/stickers@2x.zip')
        try:
            urllib.request.urlretrieve(zip_url, zip_path)
        except BaseException:
            # Download failed
            return False

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(download_dir)

        remove_files = (f'{download_dir}/*_key@2x.png {download_dir}/tab* '
                        f'{download_dir}/*.meta {download_dir}/*.zip '
                        f'{download_dir}/meta.json {download_dir}/*.key.png')
        sub = subprocess.Popen(f'rm -f {remove_files}', shell=True)
        subprocess.Popen.wait(sub)

        return True

    def fetch_line_sticker_title(self, is_emoji: bool, region='en'):
        if is_emoji:
            url = f'https://store.line.me/emojishop/product/{self._sticker_id}/{region}'
        else:
            url = f'https://store.line.me/stickershop/product/{self._sticker_id}/{region}'
        try:
            query = pyquery.PyQuery(url=url)
            sticker_title = query('p').filter('.mdCMN38Item01Ttl').text()
            if len(sticker_title) == 0:
                # selling discontinued sticker
                sticker_title = query('h2').eq(1).text()
        except urllib.error.HTTPError:
            return ""
        # sticker_title is maximum 64 characters
        return UnicodeString.normalize(sticker_title, 64)

    async def generate_sticker_name(self, is_emoji: bool, file_name=None):
        prefix = file_name
        if file_name is None:
            match = re.search(r"([a-zA-Z]+[a-zA-Z\d]*)", self.fetch_line_sticker_title(is_emoji=is_emoji))
            if match is None:
                prefix = f'line_{self._sticker_id}'
            else:
                prefix = f'{match.group(1)}_{self._sticker_id}'

        bot_info = await self._bot.get_me()
        bot_username = bot_info.username
        # sticker_name is maximum 64 characters
        sticker_name = UnicodeString.normalize(prefix, 64 - len('_by_') - len(bot_username))

        return f'{sticker_name}_by_{bot_username}'

    def unzip_sticker(self, zip_name):
        zip_path = f'{self._sticker_dir}/{zip_name}'

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(self._sticker_dir)

        for file in self._find_all_files(self._sticker_dir):
            shutil.move(file, self._sticker_dir)

        sub = subprocess.Popen(f'rm -f "{zip_path}"', shell=True)
        subprocess.Popen.wait(sub)

    @staticmethod
    def _find_all_files(directory):
        for root, _, files in os.walk(directory):
            if root == directory:
                continue

            for file in files:
                yield os.path.join(root, file)

    async def is_already_sticker_name(self, sticker_name):
        try:
            sticker_set = await self._bot.get_sticker_set(sticker_name)
        except BaseException:
            return False

        if sticker_set is None:
            return False

        if sticker_set.name == sticker_name:
            return True

        return False

    async def delete_sticker_set(self, sticker_name):
        try:
            sticker_set = await self._bot.get_sticker_set(sticker_name)
            for sticker in sticker_set.stickers:
                await self._bot.delete_sticker_from_set(sticker.file_id)
        except Exception as e:
            logger.error("Failed delete stickers.", e.args)
            traceback.print_exc()

    async def create_sticker_set(self, sticker_title, sticker_name):
        logger.info(f'Create sticker. title={sticker_title}, sticker_name={sticker_name}')
        emojis = Env.get_environment('EMOJI', default='🔗', required=False)

        is_created = False
        file_ids = []
        try:
            for png_path in sorted(glob.glob(f'{self._sticker_dir}/*.png')):
                with open(png_path, 'rb') as png:
                    uploaded_file = await self._bot.upload_sticker_file(self._user_id, png)

                file_ids.append(uploaded_file.file_id)

            if not file_ids:
                logger.warning(f'Not sticker file in {self._sticker_dir}.')
                return False

            is_created = await self._bot.create_new_sticker_set(user_id=self._user_id, name=sticker_name,
                                                                title=sticker_title,
                                                                emojis=emojis,
                                                                png_sticker=file_ids[0])
            if is_created is False:
                return False

            if len(file_ids) == 1:
                return True

            for file_id in file_ids[1:]:
                is_added = await self._bot.add_sticker_to_set(user_id=self._user_id, name=sticker_name,
                                                              emojis=emojis,
                                                              png_sticker=file_id)
                if is_added is False:
                    await self.delete_sticker_set(sticker_name)
                    return False
        except Exception as e:
            logger.error("Failed create sticker.", e.args)
            traceback.print_exc()
            if is_created is True:
                await self.delete_sticker_set(sticker_name)
            return False

        return True

    async def register_line_sticker(self, command):
        if '\n' in command:
            command = command.split('\n')[1]
        elif 'sticker' not in command and 'emojishop' not in command:
            await self._bot.reply_to(self._message, 'Please send the sticker/emoji URL.')
            return False

        is_emoji = False
        try:
            if 'emojishop' in command:
                sticker_id = re.search(r'emojishop/product/([0-9a-z]+)', str(command)).group(1)
                is_emoji = True
            else:
                sticker_id = re.search(r'\d+', str(command)).group()
        except Exception as e:
            logger.error('Can not find "Sticker id".', e.args)
            await self._bot.reply_to(self._message, 'Can not find "Sticker id".')
            traceback.print_exc()
            return False

        self.set_sticker_id(sticker_id)
        self.set_is_emoji(is_emoji)
        self.set_sticker_dir(sticker_id=sticker_id)
        if os.path.isdir(self._sticker_dir):
            logger.info(f'Already create sticker now. sticker_dir={self._sticker_dir}')
            return False

        store = StickerStore()
        try:
            entry = store.fetch_line_sticker_info(sticker_id)
        except Exception as e:
            logger.error("db access false.", e.args)
            traceback.print_exc()
            return False

        if entry is not None:
            sticker_name = entry[1]
            sticker_title = entry[2]
            await self._bot.reply_to(self._message, f'{sticker_title}\nhttps://t.me/addstickers/{sticker_name}')
            return True

        os.makedirs(self._sticker_dir, exist_ok=True)

        is_download = self.download_line_sticker()
        if is_download is False:
            return False

        self.resize_sticker()

        region = Env.get_environment('REGION', default='en', required=False)
        sticker_title = self.fetch_line_sticker_title(is_emoji=is_emoji, region=region)
        sticker_name = await self.generate_sticker_name(is_emoji=is_emoji)

        return await self._create_sticker_set(sticker_title, sticker_name, sticker_id)

    @staticmethod
    def byte_to_file(data: bytes, dest_path: str) -> None:
        with open(dest_path, mode='wb') as fw:
            fw.write(data)

    async def register_zip_sticker(self, file_id, file_name, caption) -> bool:
        basename, _ = os.path.splitext(os.path.basename(file_name))
        sticker_name = await self.generate_sticker_name(file_name=basename)
        if await self.is_already_sticker_name(sticker_name):
            msg = f'Already exist sticker_name!!\nPlease another file name.\nhttps://t.me/addstickers/{sticker_name}'
            logger.warning(msg)
            await self._bot.reply_to(self._message, msg)
            return False

        sticker_title = UnicodeString.normalize(caption, 64)
        self.set_sticker_dir(zip_file_name=basename)
        if os.path.isdir(self._sticker_dir):
            logger.warning(f'Already create sticker now. sticker_dir={self._sticker_dir}')
            return False
        os.makedirs(self._sticker_dir, exist_ok=True)

        file = await self._bot.get_file(file_id)
        read_data = await self._bot.download_file(file.file_path)
        self.byte_to_file(read_data, f'{self._sticker_dir}/{file_name}')
        self.unzip_sticker(file_name)

        self.resize_sticker()

        return await self._create_sticker_set(sticker_title, sticker_name)

    async def _create_sticker_set(self, sticker_title: str, sticker_name: str, sticker_id="-1") -> bool:
        is_created = await self.create_sticker_set(sticker_title, sticker_name)
        sub = subprocess.Popen(f'rm -r {self._sticker_dir}', shell=True)
        subprocess.Popen.wait(sub)
        if is_created is False:
            await self._bot.reply_to(self._message, 'Failed create sticker.')
            return False

        await self._bot.reply_to(self._message, f'{sticker_title}\nhttps://t.me/addstickers/{sticker_name}')

        store = StickerStore()
        try:
            store.insert_sticker_info(self._username, self._user_id, sticker_title, sticker_name, sticker_id)
        except Exception as e:
            logger.error("Insert false.", e.args)
            traceback.print_exc()

        return True


logger: logging.Logger = logging.getLogger(__name__)
