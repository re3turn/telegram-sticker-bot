#!/usr/bin/python3

import glob
import os
import urllib.request
import re
import pyquery
import zipfile
import shutil
import subprocess
import traceback
import telepot.aio
from telepot.namedtuple import StickerSet
from PIL import Image
from .unicode_string import UnicodeString
from .store import StickerStore

MAX_STICKER_SIZE = 512


class Sticker:
    def __init__(self, bot, username, user_id, chat_id, sticker_id=-1):
        self._username = username
        self._user_id = user_id
        self._chat_id = chat_id
        self._bot = bot
        self._sticker_id = sticker_id
        self._user_dir = f'./stickers/{user_id}'
        self._sticker_dir = self._user_dir
        os.makedirs(self._user_dir, exist_ok=True)

    def set_sticker_id(self, sticker_id):
        self._sticker_id = sticker_id

    def set_sticker_dir(self, sticker_id=-1, zip_file_name=None):
        if sticker_id == -1:
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
            img = img.convert('RGBA').resize((new_w, new_h), Image.ANTIALIAS)
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

        zip_url = f'http://dl.stickershop.line.naver.jp/products/0/0/1/{self._sticker_id}/iphone/stickers@2x.zip'
        try:
            urllib.request.urlretrieve(zip_url, zip_path)
        except:
            # Download failed
            return False

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(download_dir)

        remove_files = (f'{download_dir}/*_key@2x.png {download_dir}/tab* '
                        f'{download_dir}/*.meta {download_dir}/*.zip')
        sub = subprocess.Popen(f'rm -f {remove_files}', shell=True)
        subprocess.Popen.wait(sub)

        return True

    def fetch_line_sticker_title(self, region='en'):
        url = f'https://store.line.me/stickershop/product/{self._sticker_id}/{region}'
        query = pyquery.PyQuery(url=url)
        sticker_title = query('h3').filter('.mdCMN08Ttl').text()

        # sticker_title is maximum 64 characters
        return UnicodeString.normalize(sticker_title, 64)

    async def generate_sticker_name(self, file_name=None):
        prefix = file_name
        if file_name is None:
            match = re.match("([a-zA-Z\d]+)", self.fetch_line_sticker_title())
            if match is None:
                prefix = str(self._sticker_id)
            else:
                prefix = f'{match.group(1)}_{self._sticker_id}'

        bot_info = await self._bot.getMe()
        bot_username = bot_info['username']
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
            sticker_set = await self._bot.getStickerSet(sticker_name)
        except telepot.exception.TelegramError:
            return False

        if sticker_set is None:
            return False

        if str(sticker_set.get('name')) == sticker_name:
            return True

        return False

    async def delete_sticker_set(self, sticker_name):
        try:
            sticker_set = await self._bot.getStickerSet(sticker_name)
            sticker_sets = StickerSet(**sticker_set)
            for sticker in sticker_sets.stickers:
                await self._bot.deleteStickerFromSet(sticker.file_id)
        except telepot.exception.TelegramError as e:
            print("Faled delete stickers.", e.args)
            traceback.print_exc()

    async def create_sticker_set(self, sticker_title, sticker_name):
        print(f'Create sticker. title={sticker_title}, sticker_name={sticker_name}')
        emojis = os.environ.get('EMOJI')
        if emojis is None:
            emojis = '🔗'

        is_created = False
        file_ids = []
        try:
            for png_path in glob.glob(f'{self._sticker_dir}/*.png'):
                with open(png_path, 'rb') as png:
                    uploaded_file = await self._bot.uploadStickerFile(self._user_id, png)

                file_ids.append(uploaded_file['file_id'])

            if not file_ids:
                print(f'Not sticker file in {self._sticker_dir}.')
                return False

            is_created = await self._bot.createNewStickerSet(self._user_id, sticker_name, sticker_title,
                                                             file_ids[0], emojis)
            if is_created is False:
                return False

            if len(file_ids) == 1:
                return True

            for file_id in file_ids[1:]:
                is_added = await self._bot.addStickerToSet(self._user_id, sticker_name, file_id, emojis)
                if is_added is False:
                    await self.delete_sticker_set(sticker_name)
                    return False
        except telepot.exception.TelegramError as e:
            print("Faled create sticker.", e.args)
            traceback.print_exc()
            if is_created is True:
                await self.delete_sticker_set(sticker_name)
            return False

        return True

    async def register_line_sticker(self, command):
        if '\n' in command:
            command = command.split('\n')[1]
        elif 'sticker' not in command:
            await self._bot.sendMessage(self._chat_id, 'Please send the sticker URL.')
            return False

        try:
            sticker_id = re.search(r'\d+', str(command)).group()
        except:
            await self._bot.sendMessage(self._chat_id, 'Can not find "Sticker id".')
            traceback.print_exc()
            return False

        self.set_sticker_id(sticker_id)
        self.set_sticker_dir(sticker_id=int(sticker_id))
        if os.path.isdir(self._sticker_dir):
            print(f'Already create sticker now. sticker_dir={self._sticker_dir}')
            return False

        store = StickerStore()
        try:
            entry = store.fetch_line_sticker_info(sticker_id)
        except Exception as e:
            print("db access false.", e.args)
            traceback.print_exc()
            return False

        if entry is not None:
            sticker_name = entry[1]
            sticker_title = entry[2]
            await self._bot.sendMessage(self._chat_id, f'{sticker_title}\nhttps://t.me/addstickers/{sticker_name}')
            return True

        os.makedirs(self._sticker_dir, exist_ok=True)

        is_download = self.download_line_sticker()
        if is_download is False:
            return False

        self.resize_sticker()

        region = os.environ.get('REGION')
        if region is None:
            region = 'en'
        sticker_title = self.fetch_line_sticker_title(region)
        sticker_name = await self.generate_sticker_name()

        is_created = await self.create_sticker_set(sticker_title, sticker_name)
        sub = subprocess.Popen(f'rm -r {self._sticker_dir}', shell=True)
        subprocess.Popen.wait(sub)
        if is_created is False:
            await self._bot.sendMessage(self._chat_id, 'Faled create sticker.')
            return False

        await self._bot.sendMessage(self._chat_id, f'{sticker_title}\nhttps://t.me/addstickers/{sticker_name}')

        try:
            store.insert_sticker_info(self._username, self._user_id, sticker_title, sticker_name, sticker_id)
        except Exception as e:
            print("Insert false.", e.args)
            traceback.print_exc()

        return True

    async def register_zip_sticker(self, file_id, file_name, caption):
        basename, _ = os.path.splitext(os.path.basename(file_name))
        sticker_name = await self.generate_sticker_name(file_name=basename)
        if await self.is_already_sticker_name(sticker_name):
            msg = f'Already exist sticker_name!!\nPlease another file name.\nhttps://t.me/addstickers/{sticker_name}'
            print(msg)
            await self._bot.sendMessage(self._chat_id, msg)
            return False

        sticker_title = UnicodeString.normalize(caption, 64)
        self.set_sticker_dir(zip_file_name=basename)
        if os.path.isdir(self._sticker_dir):
            print(f'Already create sticker now. sticker_dir={self._sticker_dir}')
            return False
        os.makedirs(self._sticker_dir, exist_ok=True)

        await self._bot.download_file(file_id, f'{self._sticker_dir}/{file_name}')
        self.unzip_sticker(file_name)

        self.resize_sticker()

        is_created = await self.create_sticker_set(sticker_title, sticker_name)
        sub = subprocess.Popen(f'rm -r {self._sticker_dir}', shell=True)
        subprocess.Popen.wait(sub)
        if is_created is False:
            await self._bot.sendMessage(self._chat_id, 'Faled create sticker.')
            return False

        await self._bot.sendMessage(self._chat_id, f'{sticker_title}\nhttps://t.me/addstickers/{sticker_name}')

        store = StickerStore()
        try:
            store.insert_sticker_info(self._username, self._user_id, sticker_title, sticker_name)
        except Exception as e:
            print("Insert false.", e.args)
            traceback.print_exc()

        return True
