# pvm-records-bot

Discord bot that interacts with pvm-records.com.

Used exclusively for [PVM records discord](https://discord.gg/NncJz68nsD).

## Requirements

- Python 3.10+
- `pip install pipenv`

## Installation

**Token**

```
# pvm-records-bot/.env
TOKEN="<token>"
DATABASE_URL="<database>"
WEBHOOK_TOKEN="<webhook_token>"
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

## Deployment

Generate `requirements.txt`:

```
pipenv lock -r > requirements.txt
```

## Commands

| Command                      | Arguments    | Description                                           |
| ---------------------------- | ------------ | ----------------------------------------------------- |
| `enable-hiscore-roles`       | `name`       | Enable hiscore roles for the user using the command.  |
| `disable-hiscores-roles`     | -            | Disable hiscore roles for the user using the command. |
| `admin-disable-user-roles`   | `id`         | TODO                                                  |
| `admin-enable-hiscore-roles` | `id`, `name` | TODO                                                  |
| `update-roles`               |              | Update roles (used as context menu option).           |

