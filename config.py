import os

from decouple import config


class Config(object):
    basedir = os.path.abspath(os.path.dirname(__file__))

    DISCORD_TOKEN = config('DISCORD_TOKEN')
    SERVER_KEY = config('SERVER_KEY')
    SERVER_ENDPOINT = config('SERVER_ENDPOINT')
    DISCORD_CHANNEL_ID = config('DISCORD_CHANNEL_ID')


app_config = Config()
