import os

from decouple import config


class Config(object):
    @staticmethod
    def import_txt_as_list(filename):
        with open(filename, 'r') as file:
            return [line.strip() for line in file.read().splitlines()]

    basedir = os.path.abspath(os.path.dirname(__file__))

    DISCORD_TOKEN = config('DISCORD_TOKEN')
    SERVER_SECRET_KEY = config('SERVER_SECRET_KEY')
    SERVER_NAMESPACE = config('SERVER_NAMESPACE')
    HOST_URL = config('HOST_URL')
    SQLALCHEMY_DATABASE_URI = '{}://{}:{}@{}:{}/{}'.format(
        config('DB_ENGINE', default='postgresql'),
        config('DB_USERNAME', default='root'),
        config('DB_PASS', default='pass'),
        config('DB_HOST', default='localhost'),
        config('DB_PORT', default=5432),
        config('DB_NAME', default='bets')
    )
    BANNED_WORDS = import_txt_as_list(config('BANNED_WORDS_FILE'))


app_config = Config()
