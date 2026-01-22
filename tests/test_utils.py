import pytest
import dsbridge.utils as utils
from dsbridge.config import app_config

@pytest.fixture(scope="module")
def config():
    return app_config

def test_message_sanitization_safe(config):
    message = 'Greetings everyone!'
    sanitized_msg = utils.sanitize_input(message, config.BANNED_WORDS)
    assert message == sanitized_msg

def test_message_sanitization_unsafe(config):
    message = 'Go fuck yourself'
    sanitized_msg = utils.sanitize_input(message, config.BANNED_WORDS)
    assert message != sanitized_msg
