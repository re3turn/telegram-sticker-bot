#!/usr/bin/python3

import asyncio
import os
import time
import sys
import telepot.aio
from telepot.aio.loop import MessageLoop
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

    # Receive text message response
    if content_type == 'text':
        command = msg['text'].lower()
        content = f'{username}({username}):{command}'

        if 'line.me' in command:
            sticker = Sticker(bot, username, user_id, chat_id)
            await sticker.register_line_sticker(command)
        elif command == '/start':
            # bot.sendMessage(chat_id, 'Please take it https://store.line.me/ja')
            print('/start')

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
            await sticker.register_zip_sticker(file_id, file_name, caption)

    # log
    timestamp = str(time.strftime("%Y-%m-%d %H:%M:%S"))
    log = f'[{timestamp}] {content}\n'
    with open(log_name, 'a') as logfile:
        logfile.write(log)


def main():
    api_token = os.environ.get('TELEPOT_API_TOKEN')
    if api_token is None:
        sys.exit('Please set environment "TELEPOT_API_TOKEN"')

    global bot
    bot = telepot.aio.Bot(api_token)
    loop = asyncio.get_event_loop()

    loop.create_task(MessageLoop(bot, handle).run_forever())
    print('Listening...')

    loop.run_forever()


if __name__ == '__main__':
    main()
