import re

import bleach
from discord import Embed


def create_embed(title, description):
    return Embed(
        title=title,
        description=description,
    )


def remove_personal_info(message):
    patterns = {
        'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        'phone': r'\+?\d{1,3}?[-.\s]?\(?\d{1,4}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
        'credit_card': r'\b(?:\d[ -]*?){13,16}\b',
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'url': r'https?://[^\s<>"]+|www\.[^\s<>"]+',
        'html_tags': r'<[^>]+>'
    }

    for key, pattern in patterns.items():
        message = re.sub(pattern, '[REMOVED]', message)

    return message


def remove_words(input_string, banned_words):
    # Create a pattern that matches any word in the list
    pattern = r'\b(' + '|'.join(banned_words) + r')\b'

    # Use re.sub to replace the words with an empty string
    output_string = re.sub(pattern, '', input_string, flags=re.IGNORECASE)

    return output_string


def sanitize_input(user_input, banned_words):
    allowed_tags = []
    allowed_attributes = {}
    protocols = []

    # Clean the input
    sanitized_input = bleach.clean(
        user_input,
        tags=set(allowed_tags),
        attributes=allowed_attributes,
        protocols=protocols,
        strip=True
    )

    # Include custom sanitization
    sanitized_input = remove_personal_info(sanitized_input)
    sanitized_input = remove_words(sanitized_input, banned_words)

    return sanitized_input
