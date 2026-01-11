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

| Command | Usage | Description |
|---------|-------|-------------|
| `!roll` | `!roll 2d20+5` | Roll dice with modifiers. |
| `!char create` | `!char create <race>` | Start character creation. |
| `!char dr` | `!char dr <stats>` | Distribute dice points and roll stats. |
| `!char add` | `!char add <stat> <val>` | Add bonus to a stat (e.g., `!char add str 2`). |
| `!char remove` | `!char remove <stat> <val>` | Remove bonus/value from a stat. |
| `!char save` | `!char save <name>` | Save character profile. |
| `!char info` | `!char info <name>` | View character details. |
| `!char rename` | `!char rename <old> <new>` | Rename a character. |
| `!char delete` | `!char delete <name>` | Delete a character. |
| `!char edit` | `!char edit <class\|stat> ...` | Edit character class or stats. |
| `!rec` | `!rec <open\|close>` | Toggle class recommendations (Alias: `!m r`). |
| `!help` | `!help` | Display all available commands. |

**Prefixes**: `!`, `!mineria`, `!m`

## Architecture

**Cog-based Design**: Each major feature is implemented as a Discord Cog for modularity:
- `dice.py`: Dice parsing and rolling.
- `character.py`: Character creation and management logic.
- `help.py`: Dynamic help system.

**Data Layer**: JSON-based persistence in `data/` directory:
- `races.json`: Race stats and modifiers.
- `classes.json`: Class requirements.
- `characters.json`: User character profiles.
- `user_settings.json`: User preferences.

## Development

Language: **English only** in code and comments.

All game mechanics follow standard **Pathfinder 1st Edition** rules.