# 🎲 Mineria Discord Bot

A specialized Discord bot for **Pathfinder Roleplaying Game (1e)** character management. Create characters, roll dice, and manage character profiles directly from Discord.

## Features

- **Character Creation**: Create Pathfinder-compatible characters with race and class selection.
- **Dice Rolling**: Parse and roll standard RPG dice expressions (e.g., `2d20+5`, `1d10`).
- **Attribute Rolling**: Distribute points and roll character attributes using detailed dice mechanics (4d6 drop lowest).
- **Character Persistence**: Save, load, edit, and delete character profiles.
- **Class Recommendations**: Get automatic class suggestions based on rolled attributes.
- **Interactive Help System**: Built-in command manual with usage examples.

## Quick Start

### Prerequisites
- Python 3.8+
- Discord bot token in `.env` file

## Commands

**Prefixes**: `!`, `!mineria`, `!m`

### 🎲 Dice Rolling

| Command | Usage | Description |
|---------|-------|-------------|
| `!roll` | `!roll 2d20+5` | Roll dice with modifiers. Supports multiple rolls (e.g., `!roll 1d20 2d6`). |

### 👤 Character Management

| Command | Usage | Description |
|---------|-------|-------------|
| `!char create` | `!char create <race>` | Start a new character creation process (e.g., `!char create Human`). |
| `!char dr` | `!char dr <stats>` | Distribute dice points and roll stats (e.g., `!char dr STR 6 DEX 5...`). |
| `!char add` | `!char add <stat> <val>` | Add a bonus to a stat during creation (e.g., `!char add STR 2`). |
| `!char remove` | `!char remove <stat> <val>` | Remove a bonus/value from a stat during creation. |
| `!char save` | `!char save <name>` | Save the currently created character to your profile. |
| `!char info` | `!char info [name]` | View details of a saved character. Defaults to your only character if name is omitted. |
| `!char list` | `!char list` | List all characters currently saved to your profile. |
| `!char delete` | `!char delete <name>` | Permanently delete a character. |
| `!char rename` | `!char rename <old> <new>` | Rename an existing character. |
| `!char edit class` | `!char edit class <name> <class>` | Update a character's class. |
| `!char edit stat` | `!char edit stat <name> <stat> <val>` | Manually edit a specific stat value for a character. |

### 💡 Recommendations
*Evaluates your rolled stats and suggests suitable Pathfinder classes.*

| Command | Usage | Description |
|---------|-------|-------------|
| `!rec` | `!rec` | Check if class recommendations are currently enabled or disabled. (Alias: `!r`) |
| `!rec open` | `!rec open` | Enable automatic class recommendations after rolling stats. |
| `!rec close` | `!rec close` | Disable automatic class recommendations. |

### ℹ️ General & Admin

| Command | Usage | Description |
|---------|-------|-------------|
| `!help` | `!help` | Display current command manual. |
| `!backup` | `!backup` | **(Owner Only)** Trigger a manual data backup. |

## Features & Robustness

- **Comprehensive Logging**: Every interaction is logged to `logs/mineria.log` for debugging and auditing.
- **Automated Backups**: 
  - **Daily**: 08:00 AM (Retains last 7 days)
  - **Weekly**: Mondays at 08:00 AM (Retains last 5 weeks)

## Architecture

**Cog-based Design**: Each major feature is implemented as a Discord Cog for modularity:
- `log_handler.py`: Centralized event logging system.
- `dice.py`: Dice parsing and rolling.
- `character.py`: Character creation and management logic.
- `help.py`: Dynamic help system.
- `maintenance.py`: Automated and manual backups.

**Data Layer**: JSON-based persistence in `data/` directory:
- `races.json`: Race stats and modifiers.
- `classes.json`: Class requirements.
- `characters.json`: User character profiles.
- `user_settings.json`: User preferences.

## Development

Language: **English only** in code and comments.

All game mechanics follow standard **Pathfinder 1st Edition** rules.