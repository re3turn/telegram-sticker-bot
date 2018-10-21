#!/usr/bin/python3

import unicodedata


class UnicodeString:
    @staticmethod
    def _get_char_width(c):
        data = unicodedata.east_asian_width(c)
        if data == 'Na' or data == 'H':
            return 1
        return 2

    @classmethod
    def normalize(cls, string, max_width):
        index = 0
        sum_width = 0
        while index < len(string):
            c_width = cls._get_char_width(string[index])
            if sum_width + c_width > max_width:
                break
            sum_width += c_width
            index += 1
        return string[0:index]
