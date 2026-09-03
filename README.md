[![Code Coverage](https://img.shields.io/codecov/c/github/mstewart1409/discord-server-bridge)](https://img.shields.io/codecov/c/github/mstewart1409/discord-server-bridge)
[![License](https://img.shields.io/github/license/mstewart1409/discord-server-bridge)](https://img.shields.io/github/license/mstewart1409/discord-server-bridge)
[![Python Version](https://img.shields.io/badge/python-3.13-blue)](https://img.shields.io/badge/python-3.13-blue)
[![GitHub commit activity](https://img.shields.io/github/commit-activity/y/mstewart1409/discord-server-bridge.svg?color=dark-green)](https://github.com/mstewart1409/discord-server-bridge/contributors)

**Table of Contents:**

- [Introduction](#introduction)
- [Usage](#usage)
- [Development](#development)
- [Local testing](#local-testing)

# Introduction

`dsbridge` is a library that synchronizes messages between Discord and a remote server. It listens for new messages, edits, and deletions on both platforms and mirrors these actions on the other platform.

It is written in Python and uses the discord.py library to interact with Discord and python-socketio to talk to the backend server. It uses asyncio to run both bots concurrently.

The package is intended to be imported by a host application. It reads nothing from the environment: everything is passed as constructor arguments. Development is facilitated by pre-commit for managing git hooks and uv for dependency management.

Please note that this bot does not support commands in messages, and will not mirror changes to messages that were made before the bot started running.


# Usage

Construct `DSBridge` with your settings and await `start()`:

```python
import asyncio

from dsbridge import DSBridge, build_database_uri

bridge = DSBridge(
    discord_token='...',
    app_secret_key='...',
    server_namespace='/chat',
    host_url='example.com',
    database_uri=build_database_uri(name='bets', username='root', password='pass'),
    banned_words=['...'],
)

asyncio.run(bridge.start())
```

From inside an existing event loop, schedule it as a task instead:

```python
task = asyncio.create_task(bridge.start())
```

`build_database_uri` is a convenience helper; any SQLAlchemy URI can be passed to `database_uri` directly. `banned_words` takes a list of words; use `dsbridge.utils.load_banned_words(path)` to read one from a newline separated file.


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
