## 0.3.0 (2026-09-03)

### Feat

- Accept the host application's own message and channel models via `message_model` and `channel_model`
- Export `ChatChannelsMixin` and `MessageMixin` so the mapping can live in the host's registry
- Build rows with `Message.from_discord()` instead of a custom `__init__`
- Make table creation opt-out with `create_tables`

### Fix

- Create only the bridge's own tables, never the whole metadata
- Resolve a message's channel by query instead of a relationship, so hosts need not relate the two models

### BREAKING CHANGE

- `Message(data, channel)` is now `Message.from_discord(data, channel)`
- `Database.create_all()` now requires the tables to create
- `to_dict()` was removed from both models; serialisation belongs to the host

## 0.2.0 (2026-01-22)

### Fix

- Update project configuration and dependencies

## 0.1.2 (2025-12-16)

### Feat

- Handle email notifications
- Allow domain whitelist to sanitization

### Fix

- Fixed config loader relative path
- Fixed session handler on server
- Fixed session handler on server
- Fixed intents for discord bot
- Still route messages without Discord ID back to server
- Model fix
- Handle server message without discord ID
- Fix to discord bot handler
- Fix to async handler
- Async decorator
- Verison updates
- Verison updates
- Updated failed transaction decorator
- Updated reconnect handling
- Updated reconnect handling
- Updated for handling reconnect to server
- Updated for banned words list
- Updated for banned words list
- Updated for banned words list
- Updated for banned words list
- Updated for async bots
- Updated for async bots
- Updated asyncio loops
- Updated asyncio loops
- Updated asyncio loops
- Correct connection endpoint
- Handle no channel ID

### Refactor

- Changed server key name
- Standard channeling

## 0.1.1 (2024-08-28)

### Fix

- Updated versioning
- Updated versioning

## 0.1.0 (2024-08-28)

### Feat

- Generalized channel id
- Generalized channel id
- Improved discord handlers
- Improvied discord handlers
- SocketIO connection to server
- Separated modules
- Remote server link
- Handle edited and deleted messages. COnfig set from env vars. Dockerfile added. Additional logging added
- Additional logging added

### Fix

- Include discord channel id
- Updated requirements file
- Fixed server payload changes
- Fixed server payload changes
- Updated README
- Fix to build
- Fix to build
- Dependency update

### Refactor

- Cleanup
- Cleanup
- Remove empty dir
