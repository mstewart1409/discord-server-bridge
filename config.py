import os

from decouple import config


class Config(object):
    basedir = os.path.abspath(os.path.dirname(__file__))

    DISCORD_TOKEN = config('DISCORD_TOKEN')
    SERVER_KEY = config('SERVER_KEY')
    SERVER_ENDPOINT = config('SERVER_ENDPOINT')
    DISCORD_CHANNEL_ID = config('DISCORD_CHANNEL_ID')
    SQLALCHEMY_DATABASE_URI = '{}://{}:{}@{}:{}/{}'.format(
        config('DB_ENGINE', default='postgresql'),
        config('DB_USERNAME', default='root'),
        config('DB_PASS', default='pass'),
        config('DB_HOST', default='localhost'),
        config('DB_PORT', default=5432),
        config('DB_NAME', default='bets')
    )


app_config = Config()
