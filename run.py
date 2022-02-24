#!/usr/bin/python3

import logging
from app import bot
from app.log import Log


def main():
    bot.main()


logger: logging.Logger = logging.getLogger(__name__)

if __name__ == '__main__':
    Log.init_logger(log_name='run')
    logger = logging.getLogger(__name__)
    main()
