# pvm-records-bot

Discord bot that interacts with pvm-records.com.

Used exclusively for [PVM records discord](https://discord.gg/NncJz68nsD).

## Requirements

- Python 3.9+
- `pip install pipenv`

## Installation

**Token**

```
# pvm-records-bot/.env
TOKEN="<token>"
BOT_SETTINGS="copy_of_bot_settings.json"
```

**`bot_settings.json` is used by default and should be configured for the PVM Records Discord.*

**Pipenv**

Install:

```
pipenv install --skip-lock
```

Run:

```
pipenv run python main.py
```
