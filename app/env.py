#!/usr/bin/python3

import logging
import os
import sys


class Env:
    @staticmethod
    def get_environment(env_name: str, default: str = '', required: bool = False) -> str:
        env: str = os.environ.get(env_name, default)
        if required and (default == '') and (env == ''):
            sys.exit(f'Error: Please set environment "{env_name}"')

        logger.debug(f'Get environment {env_name}={env}')
        return env


logger: logging.Logger = logging.getLogger(__name__)
