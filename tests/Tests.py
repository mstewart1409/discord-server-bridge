import unittest

import dsbridge.utils as utils
from dsbridge.config import app_config


class Tests(unittest.TestCase):
    def setUp(self):
        self.config = app_config

    def test_message_sanitization_safe(self):
        message = 'Example safe message test'
        sanitized_msg = utils.sanitize_input(message, self.config.BANNED_WORDS)
        self.assertEqual(message, sanitized_msg)

    def test_message_sanitization_unsafe(self):
        message = 'Go fuck yourself'
        sanitized_msg = utils.sanitize_input(message, self.config.BANNED_WORDS)
        self.assertNotEqual(message, sanitized_msg)


if __name__ == '__main__':
    unittest.main()
