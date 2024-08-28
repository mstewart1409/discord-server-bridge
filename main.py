import logging
from dsbridge.launch import run

# Set up logging
logging.getLogger('discord').setLevel(logging.INFO)
logging.getLogger('root').setLevel(logging.INFO)
logging.getLogger(__name__).setLevel(logging.INFO)


if __name__ == '__main__':
    run()
