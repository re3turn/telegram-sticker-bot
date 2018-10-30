import nose2.tools
from app.unicode_string import UnicodeString


class TestUnicodeString:
    @nose2.tools.params(
        ('&', 1),
        ('5', 1),
        ('Z', 1),
        (' ', 1),
        ('表', 2),
        ('Ⅲ', 2),
        ('　', 2)
    )
    def test_get_char_width(self, c, ans):
        actual = UnicodeString._get_char_width(c)
        assert actual == ans

    @nose2.tools.params(
        ('abcdefghijklmnopqrstuvwxyz', 25, 'abcdefghijklmnopqrstuvwxy'),
        ('abcdefghijklmnopqrstuvwxyz', 26, 'abcdefghijklmnopqrstuvwxyz'),
        ('abcdefghijklmnopqrstuvwxyz', 27, 'abcdefghijklmnopqrstuvwxyz'),
        ('ａｂｃｄｅｆｇｈ', 10, 'ａｂｃｄｅ'),
        ('ａｂｃｄｅｆｇｈ', 9, 'ａｂｃｄ'),
        ('ａｂｃｄｅｆｇｈ', 8, 'ａｂｃｄ'),
        ('aｂcｄeｆgｈ', 5, 'aｂc'),
        ('aｂcｄeｆgｈ', 6, 'aｂcｄ'),
        ('aｂcｄeｆgｈ', 7, 'aｂcｄe')
    )
    def test_normalize(self, string, max_width, ans):
        actual = UnicodeString.normalize(string, max_width)
        assert actual == ans


if __name__ == '__main__':
    nose2.main()
