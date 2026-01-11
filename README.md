# 🎲 Mineria Discord Bot

A specialized Discord bot for **Pathfinder Roleplaying Game** character management. Create characters, roll dice, and manage character profiles directly from Discord.

## Features

- **Character Creation**: Create Pathfinder-compatible characters with race and class selection
- **Dice Rolling**: Parse and roll standard RPG dice expressions (e.g., `2d20+5`, `1d10`)
- **Attribute Rolling**: Distribute points and roll character attributes using D&D-style dice mechanics
- **Character Persistence**: Save, load, edit, and delete character profiles
- **Class Recommendations**: Get automatic class suggestions based on rolled attributes
- **Interactive Help System**: Built-in command manual with usage examples

## Quick Start

### Prerequisites
- Python 3.8+
- Discord bot token in `.env` file

## Commands

| Command | Usage | Description |
|---------|-------|-------------|
| `!roll` | `!roll 2d20+5` | Roll dice with modifiers |
| `!char create` | `!char create <race>` | Start character creation |
| `!char dr` | `!char dr <stats>` | Distribute attribute points and roll |
| `!char save` | `!char save <name>` | Save character profile |
| `!char info` | `!char info <name>` | View character details |
| `!char rename` | `!char rename <old> <new>` | Rename a character |
| `!char delete` | `!char delete <name>` | Delete a character |
| `!char edit` | `!char edit <class\|stat> ...` | Edit character class or stats |
| `!help` | `!help` | Display all available commands |

**Prefixes**: `!`, `!mineria`, `!m`

## Architecture

**Cog-based Design**: Each major feature (dice, character, help) is implemented as a Discord Cog for modularity and maintainability.

**Data Layer**: JSON-based persistence in `data/` directory:
- `races.json`: Race stats, abilities, and race points
- `classes.json`: Class definitions with primary/secondary stat requirements
- `characters.json`: User character profiles

**Character Creation Flow**:
1. User selects race → base dice points calculated (40 - Race Points)
2. User distributes dice across 6 attributes (STR, DEX, CON, INT, WIS, CHA)
3. Bot rolls (N)d6 and uses top 3 results per stat
4. Racial modifiers applied automatically
5. Class recommendations generated based on stat totals
6. Character saved to persistent storage

## Development

Language: **English only** in code and comments.

All game mechanics follow standard **Pathfinder 1st Edition** rules.