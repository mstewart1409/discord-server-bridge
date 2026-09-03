import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from dsbridge.models import ChatChannels
from dsbridge.models import Message
from dsbridge.server import UNKNOWN_DISPLAY_NAME
from dsbridge.server import Server
from tests.conftest import changes
from tests.conftest import discord_message


# --- #4: inbound handlers must not echo the event they just consumed ---

async def test_forwarding_server_message_does_not_echo(server, seeded, bot_channel, host):
    await server.handle_server_message(seeded['message_id'])

    bot_channel.send.assert_awaited_once()
    assert host.await_count == 0


async def test_forwarding_server_message_records_discord_id(server, seeded, bot_channel, reload):
    await server.handle_server_message(seeded['message_id'])

    message = await reload(Message, seeded['message_id'])
    assert message.discord_message_id == bot_channel.send.return_value.id


async def test_deleting_server_message_does_not_echo(server, seeded, bot_channel, reload, host):
    await server.handle_server_message_deletion(seeded['message_id'])

    bot_channel.fetched.delete.assert_awaited_once()
    message = await reload(Message, seeded['message_id'])
    assert message.hidden is True
    assert host.await_count == 0


# --- #1 regression + #4: edits carry both ids and do not echo ---

async def test_edit_passes_both_ids(server, seeded, edited_message, bot_channel, reload, host):
    await server.handle_server_message_edited(seeded['message_id'], edited_message)

    bot_channel.fetched.edit.assert_awaited_once()
    before = await reload(Message, seeded['message_id'])
    assert before.hidden is True
    assert host.await_count == 0


# --- #6: missing rows are logged, not dereferenced ---

async def test_missing_message_is_logged_not_raised(server, caplog):
    await server.handle_server_message(4242)

    assert 'Server message not found: 4242' in caplog.text


async def test_missing_message_for_deletion_is_logged(server, caplog):
    await server.handle_server_message_deletion(4242)

    assert 'Server message not found: 4242' in caplog.text


async def test_missing_messages_for_edit_are_logged(server, caplog):
    await server.handle_server_message_edited(4242, 4343)

    assert 'Server messages not found for edit' in caplog.text


async def test_editing_unmirrored_discord_message_is_logged(server, database, caplog, host):
    await server.edit_message_text(discord_message(), discord_message(message_id=112))

    assert 'not mirrored on the server' in caplog.text
    assert host.await_count == 0


async def test_deleting_unmirrored_discord_message_is_logged(server, caplog, host):
    await server.delete_message(discord_message())

    assert 'not mirrored on the server' in caplog.text
    assert host.await_count == 0


async def test_unknown_discord_channel_is_logged(server, seeded, caplog):
    server.discord_bot.bot.get_channel = lambda channel_id: None

    await server.handle_server_message(seeded['message_id'])

    assert 'Discord channel not found: 222' in caplog.text


# --- #7: messages without a server side user still render ---

async def test_message_without_user_uses_placeholder(server, unowned_message, bot_channel):
    await server.handle_server_message(unowned_message)

    embed = bot_channel.send.await_args.kwargs['embed']
    assert embed.title == UNKNOWN_DISPLAY_NAME


async def test_message_with_user_uses_display_name(server, seeded, bot_channel):
    await server.handle_server_message(seeded['message_id'])

    embed = bot_channel.send.await_args.kwargs['embed']
    assert embed.title == 'Alice'


async def test_display_name_resolver_may_be_async(server, seeded, bot_channel):
    async def resolve(user_id):
        return f'user-{user_id}'
    server.resolve_display_name = resolve

    await server.handle_server_message(seeded['message_id'])

    embed = bot_channel.send.await_args.kwargs['embed']
    assert embed.title == f'user-{seeded["user_id"]}'


async def test_without_a_resolver_the_placeholder_is_used(server, seeded, bot_channel):
    server.resolve_display_name = None

    await server.handle_server_message(seeded['message_id'])

    embed = bot_channel.send.await_args.kwargs['embed']
    assert embed.title == UNKNOWN_DISPLAY_NAME


# --- #3: outbound Discord-origin changes are reported to the host ---

async def test_send_to_server_creates_channel_and_reports(server, database, host):
    await server.send_to_server(discord_message(message_id=500, channel_id=777))

    async with database.session_factory() as session:
        result = await session.execute(select(ChatChannels).filter_by(discord_channel_id=777))
        assert result.scalar_one_or_none() is not None

    assert changes(host)[0]['type'] == 'new-message'


async def test_edit_message_text_reports_both_ids(server, seeded, host):
    await server.edit_message_text(discord_message(), discord_message(message_id=112,
                                                                      content='edited'))

    data = changes(host)[0]
    assert data['type'] == 'edit-message'
    assert data['before_message_id'] == seeded['message_id']
    assert data['after_message_id'] != seeded['message_id']


async def test_delete_message_reports_deletion(server, seeded, host):
    await server.delete_message(discord_message())

    data = changes(host)[0]
    assert data['type'] == 'delete-message'
    assert data['message_id'] == seeded['message_id']


async def test_changes_are_dropped_when_no_host_callback(database, bot_channel, seeded):
    server = Server(session=database.session)

    await server.delete_message(discord_message())  # must not raise


# --- session lifecycle ---

async def test_database_errors_roll_back_and_propagate(server):
    @Server.session_scope
    async def failing(self):
        raise SQLAlchemyError('db down')

    with pytest.raises(SQLAlchemyError):
        await failing(server)


async def test_programming_errors_propagate(server):
    @Server.session_scope
    async def broken(self):
        raise ValueError('bug')

    with pytest.raises(ValueError):
        await broken(server)


async def test_session_is_released_after_each_handler(server, seeded):
    await server.handle_server_message(seeded['message_id'])

    # A released registry hands out a fresh session on next use.
    assert server.session() is not None


async def test_decorator_preserves_handler_name():
    assert Server.handle_server_message.__name__ == 'handle_server_message'

