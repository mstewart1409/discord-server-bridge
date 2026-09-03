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


def test_empty_banned_words_leaves_message_untouched():
    message = 'Greetings everyone!'

    assert utils.remove_words(message, []) == message
    assert utils.remove_words(message, ['', '   ']) == message


def test_banned_words_are_matched_case_insensitively(banned_words):
    assert 'FUCK' not in utils.remove_words('FUCK this', banned_words)


def test_banned_words_only_match_whole_words():
    assert utils.remove_words('classic', ['ass']) == 'classic'


def test_regex_metacharacters_in_banned_words_are_escaped():
    assert utils.remove_words('a.c', ['a.c']) == '[REMOVED]'
    assert utils.remove_words('abc', ['a.c']) == 'abc'


@pytest.mark.parametrize('message', [
    'mail me at bob@example.com',
    'call +1 555 123 4567',
    'card 4111 1111 1111 1111',
    'ssn 123-45-6789',
    'see https://example.com/page',
    'hi <b>there</b>',
])
def test_personal_info_is_removed(message):
    assert '[REMOVED]' in utils.remove_personal_info(message)


def test_allowed_domain_emails_are_kept():
    message = 'reach me at bob@example.com or bob@other.com'

    sanitized = utils.remove_personal_info(message, allowed_domain='example.com')

    assert 'bob@example.com' in sanitized
    assert 'bob@other.com' not in sanitized


def test_sanitize_input_strips_html_tags():
    assert '<script>' not in utils.sanitize_input('<script>alert(1)</script>', [])


def test_create_embed_uses_title_and_description():
    embed = utils.create_embed('Alice', 'hello')

    assert embed.title == 'Alice'
    assert embed.description == 'hello'
