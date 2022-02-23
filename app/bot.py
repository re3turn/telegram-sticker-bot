#!/usr/bin/python3

import logging
import asyncio
import os
import sys
import telepot.aio
from telepot.aio.loop import MessageLoop

from app.env import Env
from .sticker import Sticker

log_name = 'bot.log'
bot = None


def get_username(msg):
    user_id = str(msg['from']['id'])
    username = None
    last_name = None
    if 'first_name' in msg['from']:
        username = str(msg['from']['first_name'])
    if 'last_name' in msg['from']:
        last_name = msg['from']['last_name']

    if username is None:
        if last_name is None:
            username = user_id
        else:
            username = last_name
    elif last_name is not None:
        username = f'{username}_{last_name}'

    return username


# Define the parameters of the telegram
async def handle(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    # chat_id = str(msg['chat']['id'])
    user_id = str(msg['from']['id'])
    username = get_username(msg)
    content = ''

    # Receive text message response
    if content_type == 'text':
        command = msg['text'].lower()
        content = f'{username}({user_id}):{command}'

        if 'line.me' in command:
            await bot.sendMessage(chat_id, 'Convert telegram sticker. Please wait for a few minutes...')
            sticker = Sticker(bot, username, user_id, chat_id)
            await sticker.register_line_sticker(command)
        elif command == '/start':
            # await bot.sendMessage(chat_id, 'Please take it https://store.line.me/ja')
            pass

    # Receive the file
    elif content_type == 'document':
        file_name = str(msg['document']['file_name'])
        file_id = str(msg['document']['file_id'])
        if 'caption' in msg:
            caption = str(msg['caption'])
        else:
            basename, _ = os.path.splitext(os.path.basename(file_name))
            caption = basename
        content = f'{username}({user_id}):Send documents.\n{file_name}\n{file_id}'
        if '.zip' in file_name:
            sticker = Sticker(bot, username, user_id, chat_id)
            await bot.sendMessage(chat_id, 'Convert telegram sticker. Please wait for a few minutes...')
            await sticker.register_zip_sticker(file_id, file_name, caption)

    logger.info(content)


def main():
    api_token = Env.get_environment('TELEPOT_API_TOKEN', required=True)

    global bot
    bot = telepot.aio.Bot(api_token)
    loop = asyncio.get_event_loop()

    loop.create_task(MessageLoop(bot, handle).run_forever())
    logger.info('Listening...')

    loop.run_forever()


logger: logging.Logger = logging.getLogger(__name__)

if __name__ == '__main__':
    main()
