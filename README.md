[![Build Status](https://img.shields.io/github/workflow/status/mstewart1409/discord-telegram-bridge/CI)](https://img.shields.io/github/workflow/status/mstewart1409/discord-telegram-bridge/CI)
[![Code Coverage](https://img.shields.io/codecov/c/github/mstewart1409/discord-telegram-bridge)](https://img.shields.io/codecov/c/github/mstewart1409/discord-telegram-bridge)
[![License](https://img.shields.io/github/license/mstewart1409/discord-telegram-bridge)](https://img.shields.io/github/license/mstewart1409/discord-telegram-bridge)
[![Python Version](https://img.shields.io/badge/python-3.11-blue)](https://img.shields.io/badge/python-3.11-blue)
[![GitHub commit activity](https://img.shields.io/github/commit-activity/y/mstewart1409/discord-telegram-bridge.svg?color=dark-green)](https://github.com/plotly/mstewart1409/discord-telegram-bridge/contributors)

**Table of Contents:**

- [Introduction](#introduction)
- [Development](#development)
- [Local testing](#local-testing)

# Introduction

This application is a bot that synchronizes messages between Discord and Telegram. It listens for new messages, edits, and deletions on both platforms and mirrors these actions on the other platform.

The bot is written in Python and uses the discord.py and python-telegram-bot libraries to interact with the Discord and Telegram APIs, respectively. It uses asyncio for asynchronous I/O and threading to run the Discord and Telegram bots concurrently.

The bot is designed to be run in a Docker container for easy deployment and isolation. Development is facilitated by pre-commit for managing git hooks and Poetry for dependency management.

Please note that this bot does not support commands in messages, and will not mirror changes to messages that were made before the bot started running.


# Development

In order to develop for this project you need the following tools installed:

1. [Docker Desktop](https://www.docker.com/products/docker-desktop)
2. [pre-commit](https://pre-commit.com/#install)


**Make sure you run `pre-commit install` once after cloning to initialize the git commit hooks**

# Local testing

## Using Poetry

1. Make sure that you have python and poetry installed. ([Poetry installation instructions](https://python-poetry.org/docs/#installation)) ([pyenv](https://github.com/pyenv/pyenv) or [pyenv-win](https://github.com/pyenv-win/pyenv-win) is the recommended python version manager.)
2. Clone the repo to your machine and open a terminal on the project root.
3. Run `poetry env use python 3.11.9` and then `poetry install`.
4. Run `poetry run pre-commit install`
5. Optional: Set the environment as the default for the project in your IDE for debugging and testing.
6. You should be good to go. Add any missing libraries using `poetry add`.
7. Use `poetry export --only main -o requirements.txt --without-hashes --without-urls` to update the `requirements.txt` file. (requirements.txt is needed for deployment to DE, because DE doesn't support poetry yet. pyproject.toml is used for local development and project management.)
