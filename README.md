[![Code Coverage](https://img.shields.io/codecov/c/github/mstewart1409/discord-server-bridge)](https://img.shields.io/codecov/c/github/mstewart1409/discord-server-bridge)
[![License](https://img.shields.io/github/license/mstewart1409/discord-server-bridge)](https://img.shields.io/github/license/mstewart1409/discord-server-bridge)
[![Python Version](https://img.shields.io/badge/python-3.13-blue)](https://img.shields.io/badge/python-3.13-blue)
[![GitHub commit activity](https://img.shields.io/github/commit-activity/y/mstewart1409/discord-server-bridge.svg?color=dark-green)](https://github.com/mstewart1409/discord-server-bridge/contributors)

**Table of Contents:**

- [Introduction](#introduction)
- [Usage](#usage)
- [Server contract](#server-contract)
- [Development](#development)
- [Local testing](#local-testing)

# Introduction

`dsbridge` is a library that synchronizes messages between Discord and the application that hosts it. It listens for new messages, edits, and deletions on both sides and mirrors these actions on the other.

It is written in Python and uses the discord.py library to interact with Discord, and async SQLAlchemy for the shared database. The host application drives it through plain method calls; the bridge owns no network connection of its own beyond Discord.

The package is intended to be imported by a host application. It reads nothing from the environment: everything is passed as constructor arguments. Development is facilitated by pre-commit for managing git hooks and uv for dependency management.

Please note that this bot does not support commands in messages, and will not mirror changes to messages that were made before the bot started running.


# Usage

Construct `DSBridge` with your settings and await `start()`:

```python
import asyncio

from dsbridge import DSBridge, build_database_uri


async def on_change(payload):
    """Called for every change that originated on Discord.

    `payload` is a plain dict. Do whatever your application needs with it:
    broadcast it to your own clients, log it, or ignore it.
    """
    await my_socketio_server.emit('chat-message', payload, namespace='/chat')


bridge = DSBridge(
    discord_token='...',
    database_uri=build_database_uri(name='bets', username='root', password='pass'),
    on_change=on_change,
    banned_words=['...'],
)

asyncio.run(bridge.start())
```

From inside an existing event loop, schedule it as a task instead:

```python
task = asyncio.create_task(bridge.start())
```

`build_database_uri` is a convenience helper; any SQLAlchemy URI can be passed to `database_uri` directly, provided it names an **asyncio** driver such as `postgresql+psycopg://` or `postgresql+asyncpg://`. `banned_words` takes a list of words. `database_pool_size` and `database_max_overflow` tune the SQLAlchemy connection pool; leave them unset to keep SQLAlchemy's defaults.

## Server contract

The bridge runs in your process, so the two directions are just function calls.

**Server to Discord.** When a change originates in your application, call the bridge directly:

```python
await bridge.server_bot.handle_server_message(message.id)
await bridge.server_bot.handle_server_message_edited(old.id, new.id)
await bridge.server_bot.handle_server_message_deletion(message.id)
```

**Discord to server.** The bridge writes the row itself, then calls your `on_change` with a plain dict:

```python
{'type': 'new-message', 'message_id': 1}
{'type': 'edit-message', 'before_message_id': 1, 'after_message_id': 2}
{'type': 'delete-message', 'message_id': 1}
```

What you do with it is up to you — the bridge has no opinion and no transport of its own. `on_change` is optional; omit it and changes are simply persisted.

The bridge never acknowledges a change back to you: the handlers above mirror onto Discord and record the resulting `discord_message_id` on the row, and `on_change` fires only for changes that originated on Discord. There is no loop between the two.


# Development

In order to develop for this project you need the following tools installed:

1. [uv](https://docs.astral.sh/uv/getting-started/installation/)
2. [pre-commit](https://pre-commit.com/#install)


**Make sure you run `pre-commit install` once after cloning to initialize the git commit hooks**

# Local testing

1. Clone the repo to your machine and open a terminal on the project root.
2. Run `uv sync` to create the virtual environment and install all dependencies, including the dev group.
3. Run `uv run pre-commit install`.
4. Optional: Set `.venv` as the project interpreter in your IDE for debugging and testing.
5. Run the tests with `uv run pytest` and the linter with `uv run ruff check .`.
6. Add any missing libraries using `uv add` (or `uv add --dev` for development-only dependencies).
