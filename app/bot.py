#!/usr/bin/python3

import logging
import os
from telebot.async_telebot import AsyncTeleBot
from telebot import types
import asyncio

from app.env import Env
from app.log import Log
from app.sticker import Sticker

log_name = 'bot.log'
api_token = Env.get_environment('API_TOKEN', required=True)

bot = AsyncTeleBot(api_token, parse_mode=None)


def get_username(msg: types.Message):
    user_id = msg.from_user.id
    username = None
    last_name = None
    if msg.from_user.first_name is not None:
        username = msg.from_user.first_name
    if msg.from_user.last_name is not None:
        last_name = msg.from_user.last_name

    if username is None:
        if last_name is None:
            username = user_id
        else:
            username = last_name
    elif last_name is not None:
        username = f'{username}_{last_name}'

    return username


@bot.message_handler(func=lambda message: True, content_types=['text'])
async def new_message(message: types.Message):
    user_id: int = message.from_user.id
    username: str = get_username(message)
    command = message.text.lower()
    content = f'{username}({user_id}):{command}'

    if 'line.me' in command:
        await bot.send_message(message.chat.id, 'Convert telegram sticker. Please wait for a few minutes...')
        sticker = Sticker(bot, username, user_id, message)
        await sticker.register_line_sticker(command)
    elif command == '/start':
        # await bot.sendMessage(chat_id, 'Please take it https://store.line.me/ja')
        pass

    logger.info(content)


@bot.message_handler(func=lambda message: True, content_types=['document'])
async def new_doc(message):
    user_id: int = message.from_user.id
    username: str = get_username(message)

    file_name = message.document.file_name
    file_id = message.document.file_id
    if message.caption is not None and len(message.caption) > 0:
        caption = message.caption
    else:
        basename, _ = os.path.splitext(os.path.basename(file_name))
        caption = basename
    content = f'{username}({user_id}):Send documents.\n{file_name}\n{file_id}'
    if '.zip' in file_name:
        sticker = Sticker(bot, username, user_id, message)
        await bot.send_message(message.chat.id, 'Convert telegram sticker. Please wait for a few minutes...')
        await sticker.register_zip_sticker(file_id, file_name, caption)

    logger.info(content)


def main():
    logger.info('Listening...')
    asyncio.run(bot.polling())


logger: logging.Logger = logging.getLogger(__name__)

if __name__ == '__main__':
    Log.init_logger(log_name='bot')
    logger = logging.getLogger(__name__)
    main()
