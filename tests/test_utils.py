import pytest
import dsbridge.utils as utils

@pytest.fixture(scope="module")
def banned_words():
    return ['fuck', 'shit']

def test_message_sanitization_safe(banned_words):
    message = 'Greetings everyone!'
    sanitized_msg = utils.sanitize_input(message, banned_words)
    assert message == sanitized_msg

def test_message_sanitization_unsafe(banned_words):
    message = 'Go fuck yourself'
    sanitized_msg = utils.sanitize_input(message, banned_words)
    assert message != sanitized_msg
