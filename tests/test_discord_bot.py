from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import discord
import pytest

from dsbridge.discord_bot import DiscordBot
from tests.conftest import discord_message

CHAT = 222
OTHER = 444


def message(content='hello', channel_id=CHAT, bot=False, webhook_id=None, staff=False, dm=False):
    msg = discord_message(channel_id=channel_id, content=content)
    msg.author = MagicMock(spec=discord.Member)
    msg.author.bot = bot
    msg.channel.permissions_for.return_value.manage_messages = staff
    msg.webhook_id = webhook_id
    msg.guild = None if dm else MagicMock()
    msg.delete = AsyncMock()
    return msg


@pytest.fixture
def bot():
    instance = DiscordBot('token', banned_words=['shit'], channel_ids={CHAT})
    instance.init_bot(AsyncMock())
    return instance


def forwarded(bot):
    return bot.server_bot.send_to_server.await_count


@pytest.mark.parametrize('author', [{'bot': True}, {'webhook_id': 555}])
async def test_bot_and_webhook_posts_with_a_link_are_left_alone(bot, author):
    msg = message('see https://innovisionlabs.co.uk & join', **author)

    await bot.bot.on_message(msg)

    msg.delete.assert_not_awaited()
    assert forwarded(bot) == 0


async def test_a_banned_word_in_the_chat_channel_is_deleted(bot):
    msg = message('this is shit')

    await bot.bot.on_message(msg)

    msg.delete.assert_awaited_once()
    assert forwarded(bot) == 0


async def test_a_link_from_a_member_is_still_deleted(bot):
    msg = message('see https://example.com')

    await bot.bot.on_message(msg)

    msg.delete.assert_awaited_once()


async def test_a_message_in_another_channel_is_ignored(bot):
    msg = message('this is shit https://example.com', channel_id=OTHER)

    await bot.bot.on_message(msg)

    msg.delete.assert_not_awaited()
    assert forwarded(bot) == 0


async def test_an_escaped_tag_is_still_a_change(bot):
    msg = message('&lt;script&gt;alert(1)&lt;/script&gt;')

    await bot.bot.on_message(msg)

    msg.delete.assert_awaited_once()


async def test_a_direct_message_is_still_mirrored(bot):
    await bot.bot.on_message(message('hello', channel_id=OTHER, dm=True))

    assert forwarded(bot) == 1


async def test_an_ampersand_alone_is_not_a_change(bot):
    msg = message('Tom & Jerry')

    await bot.bot.on_message(msg)

    msg.delete.assert_not_awaited()
    assert forwarded(bot) == 1


async def test_a_typed_entity_is_not_a_change(bot):
    msg = message('&lt;3 the 2UP alerts')

    await bot.bot.on_message(msg)

    msg.delete.assert_not_awaited()


async def test_staff_posts_with_a_link_are_mirrored_not_deleted(bot):
    msg = message('BetTOM & 36Vegas: https://innovisionlabs.co.uk', staff=True)

    await bot.bot.on_message(msg)

    msg.delete.assert_not_awaited()
    assert forwarded(bot) == 1


async def test_edits_and_deletes_outside_the_chat_channel_are_ignored(bot):
    msg = message(channel_id=OTHER)

    await bot.bot.on_message_edit(msg, msg)
    await bot.bot.on_message_delete(msg)

    bot.server_bot.edit_message_text.assert_not_awaited()
    bot.server_bot.delete_message.assert_not_awaited()


async def test_without_channel_ids_every_channel_is_moderated():
    instance = DiscordBot('token', banned_words=['shit'])
    instance.init_bot(AsyncMock())
    msg = message('this is shit', channel_id=OTHER)

    await instance.bot.on_message(msg)

    msg.delete.assert_awaited_once()
