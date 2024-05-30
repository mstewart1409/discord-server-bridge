import os

from decouple import config


class Config(object):
    basedir = os.path.abspath(os.path.dirname(__file__))

    DISCORD_TOKEN = config('DISCORD_TOKEN')
    TELEGRAM_TOKEN = config('TELEGRAM_TOKEN')
    TELEGRAM_CHAT_ID = config('TELEGRAM_CHAT_ID')
    DISCORD_CHANNEL_ID = config('DISCORD_CHANNEL_ID')


app_config = Config()
