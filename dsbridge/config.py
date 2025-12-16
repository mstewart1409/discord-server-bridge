import os

from decouple import config


class Config(object):
    @staticmethod
    def import_txt_as_list(filename):
        # Get the directory where this config.py file is located
        config_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(config_dir, filename)

        output = []
        try:
            with open(file_path, 'r') as f:
                output = f.read().split('\n')
        except FileNotFoundError:
            print(f"Warning: File {file_path} not found")
        return output

    basedir = os.path.abspath(os.path.dirname(__file__))

    DISCORD_TOKEN = config('DISCORD_TOKEN')
    APP_SECRET_KEY = config('APP_SECRET_KEY')
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
